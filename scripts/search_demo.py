from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import connect, fetch_observation_summary


def unique_image_ids(rows: list[sqlite3.Row]) -> list[str]:
    return sorted({row["image_id"] for row in rows})


def search(conn: sqlite3.Connection, args: argparse.Namespace) -> list[str]:
    ids: set[str] | None = None

    def intersect(next_ids: list[str]) -> None:
        nonlocal ids
        next_set = set(next_ids)
        ids = next_set if ids is None else ids & next_set

    if args.keyword:
        pattern = f"%{args.keyword}%"
        rows = conn.execute(
            """
            SELECT image_id FROM images
            WHERE scene_summary LIKE ? OR area_type LIKE ?
            UNION
            SELECT image_id FROM objects
            WHERE name LIKE ? OR category LIKE ? OR location_description LIKE ?
               OR state LIKE ? OR attributes LIKE ? OR inspection_relevance LIKE ?
               OR suggested_action LIKE ?
            UNION
            SELECT image_id FROM abnormalities
            WHERE type LIKE ? OR description LIKE ? OR related_objects LIKE ? OR suggested_action LIKE ?
            UNION
            SELECT image_id FROM robot_view
            WHERE visible_summary LIKE ? OR visible_area LIKE ? OR key_visible_elements LIKE ?
               OR lighting_condition_description LIKE ? OR occlusions_or_blind_spots LIKE ?
               OR image_quality LIKE ? OR robot_view_limitation LIKE ?
            UNION
            SELECT image_id FROM light_inspection
            WHERE room_lighting_state LIKE ? OR ambient_light_level LIKE ?
               OR visible_light_sources LIKE ? OR switch_visibility LIKE ?
               OR need_turn_off LIKE ? OR evidence LIKE ? OR suggested_action LIKE ?
            UNION
            SELECT image_id FROM switches
            WHERE location_description LIKE ? OR state LIKE ? OR evidence LIKE ?
            UNION
            SELECT image_id FROM relations WHERE relation_text LIKE ?
            UNION
            SELECT image_id FROM uncertainty WHERE text LIKE ?
            """,
            (pattern,) * 32,
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.risk:
        rows = conn.execute(
            """
            SELECT image_id FROM objects WHERE risk_level = ?
            UNION
            SELECT image_id FROM abnormalities WHERE risk_level = ?
            """,
            (args.risk, args.risk),
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.area:
        rows = conn.execute(
            "SELECT image_id FROM images WHERE area_type LIKE ? OR area_hint LIKE ?",
            (f"%{args.area}%", f"%{args.area}%"),
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.abnormal:
        rows = conn.execute("SELECT DISTINCT image_id FROM abnormalities").fetchall()
        intersect(unique_image_ids(rows))

    if args.uncertain:
        rows = conn.execute("SELECT DISTINCT image_id FROM uncertainty").fetchall()
        intersect(unique_image_ids(rows))

    if args.light_on:
        rows = conn.execute(
            "SELECT image_id FROM light_inspection WHERE room_lighting_state = 'on'"
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.switch_visible:
        rows = conn.execute(
            """
            SELECT image_id FROM light_inspection WHERE switch_visibility IN ('visible', 'partially_visible')
            UNION
            SELECT image_id FROM switches WHERE visible = 1
            """
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.need_action:
        rows = conn.execute(
            "SELECT image_id FROM light_inspection WHERE need_turn_off = 'yes'"
        ).fetchall()
        intersect(unique_image_ids(rows))

    if args.task == "light_off":
        rows = conn.execute(
            """
            SELECT image_id FROM light_inspection
            WHERE room_lighting_state = 'on'
               OR switch_visibility IN ('visible', 'partially_visible')
               OR need_turn_off IN ('yes', 'uncertain')
            """
        ).fetchall()
        intersect(unique_image_ids(rows))

    if ids is None:
        rows = conn.execute("SELECT image_id FROM images ORDER BY image_id").fetchall()
        return unique_image_ids(rows)
    return sorted(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search semantic observation SQLite DB.")
    parser.add_argument("--db-path", default="outputs/semantic_observations.sqlite", help="SQLite database path.")
    parser.add_argument("--keyword", help="Search object, summary, abnormality, relation, or uncertainty text.")
    parser.add_argument("--risk", choices=["none", "low", "medium", "high"], help="Filter by risk level.")
    parser.add_argument("--area", help="Filter by area type or area hint.")
    parser.add_argument("--abnormal", action="store_true", help="Only show images with abnormalities.")
    parser.add_argument("--uncertain", action="store_true", help="Only show images with uncertainty notes.")
    parser.add_argument("--light-on", action="store_true", help="Only show images where lights are judged on.")
    parser.add_argument("--switch-visible", action="store_true", help="Only show images with visible or partially visible light switches.")
    parser.add_argument("--need-action", action="store_true", help="Only show images where turn-off action is recommended.")
    parser.add_argument("--task", choices=["light_off"], help="Task-oriented preset query.")
    args = parser.parse_args()

    conn = connect((ROOT / args.db_path).resolve())
    image_ids = search(conn, args)
    results = fetch_observation_summary(conn, image_ids)
    conn.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
