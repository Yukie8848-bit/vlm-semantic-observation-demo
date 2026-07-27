from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect
from src.json_utils import read_json
from src.scene_db import create_scene_tables, insert_scene_observation
from src.schema import SceneDescriptionObservation


def resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build SQLite DB from generic scene-description JSON files."
    )
    parser.add_argument(
        "--json-dir",
        action="append",
        dest="json_dirs",
        help="JSON directory. Repeat this option to import multiple directories.",
    )
    parser.add_argument(
        "--db-path",
        default="outputs/scene_observations.sqlite",
        help="SQLite output path.",
    )
    args = parser.parse_args()

    json_dirs = args.json_dirs or ["outputs/json_scene_description"]
    resolved_dirs = [resolve_project_path(value) for value in json_dirs]
    missing_dirs = [path for path in resolved_dirs if not path.is_dir()]
    if missing_dirs:
        parser.error(
            "JSON directory not found: " + ", ".join(str(path) for path in missing_dirs)
        )

    json_paths = [
        path
        for directory in resolved_dirs
        for path in sorted(directory.glob("*.json"))
        if not path.name.endswith(".failed.json")
    ]
    if not json_paths:
        parser.error("No valid JSON files found in the selected directories.")

    db_path = resolve_project_path(args.db_path)
    conn = connect(db_path)
    create_scene_tables(conn)

    inserted = 0
    skipped = 0
    duplicate_ids = 0
    seen_ids: set[str] = set()
    for json_path in tqdm(json_paths, desc="Build scene SQLite"):
        try:
            data = read_json(json_path)
            if "scene_brief" not in data or not isinstance(data.get("items"), list):
                raise ValueError("not a generic scene-description JSON")
            obs = SceneDescriptionObservation.model_validate(data)
            if obs.image_id in seen_ids:
                duplicate_ids += 1
            seen_ids.add(obs.image_id)
            insert_scene_observation(conn, obs)
            inserted += 1
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            skipped += 1
            print(f"Skip invalid JSON {json_path}: {exc}")

    conn.commit()
    conn.close()
    print(
        "Done. "
        f"files_inserted={inserted}, unique_images={len(seen_ids)}, "
        f"duplicate_ids={duplicate_ids}, skipped={skipped}, db={db_path}"
    )


if __name__ == "__main__":
    main()
