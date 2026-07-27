from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect
from src.scene_db import find_scene_image_ids_by_item, fetch_scene_summaries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search generic scene observations by visible item name."
    )
    parser.add_argument(
        "--db-path",
        default="outputs/scene_observations.sqlite",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--item",
        "--object",
        dest="item",
        help="Item-name substring, such as refrigerator, 冰箱, or switch.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum item confidence from 0 to 1.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of matching images.",
    )
    args = parser.parse_args()

    if not 0.0 <= args.min_confidence <= 1.0:
        parser.error("--min-confidence must be between 0 and 1.")
    if args.limit < 1:
        parser.error("--limit must be at least 1.")

    db_path = Path(args.db_path)
    db_path = db_path.resolve() if db_path.is_absolute() else (ROOT / db_path).resolve()
    if not db_path.is_file():
        parser.error(f"SQLite database not found: {db_path}")

    conn = connect(db_path)
    try:
        image_ids = find_scene_image_ids_by_item(
            conn,
            item_keyword=args.item,
            min_confidence=args.min_confidence,
            limit=args.limit,
        )
        results = fetch_scene_summaries(conn, image_ids)
    finally:
        conn.close()

    output = {
        "query": {
            "item": args.item,
            "min_confidence": args.min_confidence,
            "limit": args.limit,
        },
        "match_count": len(results),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
