from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect, create_tables, insert_observation
from src.json_utils import read_json
from src.schema import SemanticObservation


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SQLite DB from semantic observation JSON files.")
    parser.add_argument("--json-dir", default="outputs/json", help="Directory containing valid observation JSON files.")
    parser.add_argument("--db-path", default="outputs/semantic_observations.sqlite", help="SQLite output path.")
    args = parser.parse_args()

    json_dir = (ROOT / args.json_dir).resolve()
    db_path = (ROOT / args.db_path).resolve()
    json_paths = sorted(path for path in json_dir.glob("*.json") if not path.name.endswith(".failed.json"))

    conn = connect(db_path)
    create_tables(conn)

    inserted = 0
    skipped = 0
    for json_path in tqdm(json_paths, desc="Build SQLite"):
        try:
            obs = SemanticObservation.model_validate(read_json(json_path))
            insert_observation(conn, obs)
            inserted += 1
        except ValidationError as exc:
            skipped += 1
            print(f"Skip invalid JSON {json_path}: {exc}")

    conn.commit()
    conn.close()
    print(f"Done. inserted={inserted}, skipped={skipped}, db={db_path}")


if __name__ == "__main__":
    main()
