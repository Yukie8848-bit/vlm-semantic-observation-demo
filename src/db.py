from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import SemanticObservation


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS images;
        DROP TABLE IF EXISTS objects;
        DROP TABLE IF EXISTS abnormalities;
        DROP TABLE IF EXISTS relations;
        DROP TABLE IF EXISTS uncertainty;
        DROP TABLE IF EXISTS robot_view;
        DROP TABLE IF EXISTS light_inspection;
        DROP TABLE IF EXISTS switches;

        CREATE TABLE images (
            image_id TEXT PRIMARY KEY,
            image_path TEXT,
            timestamp TEXT,
            area_hint TEXT,
            area_type TEXT,
            scene_summary TEXT
        );

        CREATE TABLE objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            name TEXT,
            category TEXT,
            location_description TEXT,
            state TEXT,
            attributes TEXT,
            inspection_relevance TEXT,
            risk_level TEXT,
            suggested_action TEXT,
            confidence REAL
        );

        CREATE TABLE robot_view (
            image_id TEXT PRIMARY KEY,
            visible_summary TEXT,
            visible_area TEXT,
            key_visible_elements TEXT,
            lighting_condition_description TEXT,
            occlusions_or_blind_spots TEXT,
            image_quality TEXT,
            robot_view_limitation TEXT
        );

        CREATE TABLE light_inspection (
            image_id TEXT PRIMARY KEY,
            room_lighting_state TEXT,
            ambient_light_level TEXT,
            visible_light_sources TEXT,
            switch_visibility TEXT,
            need_turn_off TEXT,
            evidence TEXT,
            suggested_action TEXT,
            confidence REAL
        );

        CREATE TABLE switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            visible INTEGER,
            location_description TEXT,
            state TEXT,
            evidence TEXT,
            confidence REAL
        );

        CREATE TABLE abnormalities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            type TEXT,
            description TEXT,
            related_objects TEXT,
            risk_level TEXT,
            suggested_action TEXT
        );

        CREATE TABLE relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            relation_text TEXT
        );

        CREATE TABLE uncertainty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT,
            text TEXT
        );
        """
    )


def insert_observation(conn: sqlite3.Connection, obs: "SemanticObservation") -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO images
        (image_id, image_path, timestamp, area_hint, area_type, scene_summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (obs.image_id, obs.image_path, obs.timestamp, obs.area_hint, obs.area_type, obs.scene_summary),
    )

    view = obs.robot_view
    conn.execute(
        """
        INSERT OR REPLACE INTO robot_view
        (image_id, visible_summary, visible_area, key_visible_elements,
         lighting_condition_description, occlusions_or_blind_spots, image_quality, robot_view_limitation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obs.image_id,
            view.visible_summary,
            view.visible_area,
            json.dumps(view.key_visible_elements, ensure_ascii=False),
            view.lighting_condition_description,
            json.dumps(view.occlusions_or_blind_spots, ensure_ascii=False),
            view.image_quality,
            view.robot_view_limitation,
        ),
    )

    for obj in obs.objects:
        conn.execute(
            """
            INSERT INTO objects
            (image_id, name, category, location_description, state, attributes,
             inspection_relevance, risk_level, suggested_action, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs.image_id,
                obj.name,
                obj.category,
                obj.location_description,
                obj.state,
                json.dumps(obj.attributes, ensure_ascii=False),
                obj.inspection_relevance,
                obj.risk_level,
                obj.suggested_action,
                obj.confidence,
            ),
        )

    light = obs.light_inspection
    conn.execute(
        """
        INSERT OR REPLACE INTO light_inspection
        (image_id, room_lighting_state, ambient_light_level, visible_light_sources,
         switch_visibility, need_turn_off, evidence, suggested_action, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obs.image_id,
            light.room_lighting_state,
            light.ambient_light_level,
            json.dumps(light.visible_light_sources, ensure_ascii=False),
            light.switch_visibility,
            light.need_turn_off,
            light.evidence,
            light.suggested_action,
            light.confidence,
        ),
    )

    for switch in light.switches:
        conn.execute(
            """
            INSERT INTO switches
            (image_id, visible, location_description, state, evidence, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                obs.image_id,
                int(switch.visible),
                switch.location_description,
                switch.state,
                switch.evidence,
                switch.confidence,
            ),
        )

    for abnormality in obs.abnormalities:
        conn.execute(
            """
            INSERT INTO abnormalities
            (image_id, type, description, related_objects, risk_level, suggested_action)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                obs.image_id,
                abnormality.type,
                abnormality.description,
                json.dumps(abnormality.related_objects, ensure_ascii=False),
                abnormality.risk_level,
                abnormality.suggested_action,
            ),
        )

    for relation in obs.spatial_relations:
        conn.execute("INSERT INTO relations (image_id, relation_text) VALUES (?, ?)", (obs.image_id, relation))

    for text in obs.uncertainty:
        conn.execute("INSERT INTO uncertainty (image_id, text) VALUES (?, ?)", (obs.image_id, text))


def _decode_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return parsed if isinstance(parsed, list) else [str(parsed)]


def fetch_observation_summary(conn: sqlite3.Connection, image_ids: list[str]) -> list[dict]:
    if not image_ids:
        return []
    placeholders = ",".join("?" for _ in image_ids)
    images = conn.execute(
        f"SELECT * FROM images WHERE image_id IN ({placeholders}) ORDER BY image_id",
        image_ids,
    ).fetchall()

    results = []
    for image in images:
        image_id = image["image_id"]
        objects = conn.execute("SELECT * FROM objects WHERE image_id = ?", (image_id,)).fetchall()
        abnormalities = conn.execute("SELECT * FROM abnormalities WHERE image_id = ?", (image_id,)).fetchall()
        robot_view = conn.execute("SELECT * FROM robot_view WHERE image_id = ?", (image_id,)).fetchone()
        light = conn.execute("SELECT * FROM light_inspection WHERE image_id = ?", (image_id,)).fetchone()
        switches = conn.execute("SELECT * FROM switches WHERE image_id = ?", (image_id,)).fetchall()
        relations = conn.execute("SELECT relation_text FROM relations WHERE image_id = ?", (image_id,)).fetchall()
        uncertainties = conn.execute("SELECT text FROM uncertainty WHERE image_id = ?", (image_id,)).fetchall()
        object_dicts = [dict(row) for row in objects]
        for obj in object_dicts:
            obj["attributes"] = _decode_json_list(obj.get("attributes"))

        abnormality_dicts = [dict(row) for row in abnormalities]
        for abnormality in abnormality_dicts:
            abnormality["related_objects"] = _decode_json_list(abnormality.get("related_objects"))

        robot_view_dict = dict(robot_view) if robot_view else {}
        if robot_view_dict:
            robot_view_dict["key_visible_elements"] = _decode_json_list(robot_view_dict.get("key_visible_elements"))
            robot_view_dict["occlusions_or_blind_spots"] = _decode_json_list(
                robot_view_dict.get("occlusions_or_blind_spots")
            )

        light_dict = dict(light) if light else {}
        if light_dict:
            light_dict["visible_light_sources"] = _decode_json_list(light_dict.get("visible_light_sources"))
            light_dict["switches"] = [dict(row) for row in switches]
            for switch in light_dict["switches"]:
                switch["visible"] = bool(switch["visible"])

        results.append(
            {
                "image_path": image["image_path"],
                "area_type": image["area_type"],
                "scene_summary": image["scene_summary"],
                "robot_view": robot_view_dict,
                "light_inspection": light_dict,
                "objects": object_dicts,
                "abnormalities": abnormality_dicts,
                "spatial_relations": [row["relation_text"] for row in relations],
                "uncertainty": [row["text"] for row in uncertainties],
            }
        )
    return results
