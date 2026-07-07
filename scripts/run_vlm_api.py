from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image
from pydantic import ValidationError
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.json_utils import extract_json_object, write_json
from src.prompt import SYSTEM_PROMPT, build_user_prompt
from src.scene_description_prompt import SCENE_DESCRIPTION_SYSTEM_PROMPT, build_scene_description_prompt
from src.schema import SceneDescriptionObservation, SemanticObservation
from src.vlm_client import VLMClient


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PROMPT_MODES = {"light_off", "scene_description"}


def get_prompt_config(prompt_mode: str):
    if prompt_mode == "scene_description":
        return SCENE_DESCRIPTION_SYSTEM_PROMPT, build_scene_description_prompt, SceneDescriptionObservation
    return SYSTEM_PROMPT, build_user_prompt, SemanticObservation


def resolve_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()


def iter_images(image_dir: Path) -> list[Path]:
    return sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)


def stable_image_id(image_path: Path, image_dir: Path) -> str:
    try:
        relative = image_path.relative_to(image_dir)
        prefix = image_dir.name
    except ValueError:
        relative = image_path.name
        prefix = image_path.parent.name
    parts = [prefix, *Path(relative).with_suffix("").parts]
    return "_".join(part for part in parts if part)


def display_image_path(image_path: Path) -> str:
    try:
        return image_path.relative_to(ROOT).as_posix()
    except ValueError:
        return image_path.as_posix()


def validate_image(image_path: Path) -> None:
    with Image.open(image_path) as img:
        img.verify()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VLM API over local keyframe images.")
    parser.add_argument("--image-dir", default="data/images", help="Directory containing input images.")
    parser.add_argument("--output-dir", default="outputs/json", help="Directory for output JSON files.")
    parser.add_argument("--area-hint", default=None, help="Optional area hint written into every prompt.")
    parser.add_argument("--overwrite", action="store_true", help="Reprocess images with existing JSON outputs.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N images for quick tests.")
    parser.add_argument("--debug", action="store_true", help="Print per-image progress and errors.")
    parser.add_argument(
        "--prompt-mode",
        choices=sorted(PROMPT_MODES),
        default="light_off",
        help="Prompt/schema mode: light_off for turn-off inspection, scene_description for generic robot view.",
    )
    args = parser.parse_args()

    image_dir = resolve_path(args.image_dir)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    images = iter_images(image_dir)
    if args.limit is not None:
        images = images[: args.limit]
    if not images:
        print(f"No images found in {image_dir}")
        return

    client = VLMClient()
    system_prompt, build_prompt, observation_schema = get_prompt_config(args.prompt_mode)
    ok_count = 0
    fail_count = 0

    for image_path in tqdm(images, desc=f"VLM {args.prompt_mode}"):
        image_id = stable_image_id(image_path, image_dir)
        output_path = output_dir / f"{image_id}.json"
        if output_path.exists() and not args.overwrite:
            if args.debug:
                print(f"Skip existing: {output_path}", flush=True)
            continue

        prompt_image_path = display_image_path(image_path)
        raw_response = ""
        try:
            if args.debug:
                print(f"\n[{image_id}] validating image: {image_path}", flush=True)
            validate_image(image_path)
            if args.debug:
                print(f"[{image_id}] calling VLM API...", flush=True)
            raw_response = client.analyze_image(
                image_path=image_path,
                system_prompt=system_prompt,
                user_prompt=build_prompt(image_id, prompt_image_path, args.area_hint),
            )
            if args.debug:
                print(f"[{image_id}] parsing response...", flush=True)
            data = extract_json_object(raw_response)
            data.setdefault("image_id", image_id)
            data.setdefault("image_path", prompt_image_path)
            data.setdefault("area_hint", args.area_hint)
            data["raw_model_response"] = raw_response
            observation = observation_schema.model_validate(data)
            write_json(output_path, observation.model_dump())
            if args.debug:
                print(f"[{image_id}] saved: {output_path}", flush=True)
            ok_count += 1
        except (ValidationError, Exception) as exc:
            fail_count += 1
            write_json(
                output_path.with_suffix(".failed.json"),
                {
                    "image_id": image_id,
                    "image_path": prompt_image_path,
                    "error": str(exc),
                    "raw_model_response": raw_response,
                },
            )
            if args.debug:
                print(f"[{image_id}] failed: {exc}", flush=True)

    print(f"Done. valid={ok_count}, failed={fail_count}, output_dir={output_dir}")


if __name__ == "__main__":
    main()
