from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import SceneDescriptionObservation


def create_scene_tables(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        DROP TABLE IF EXISTS scene_uncertainty;
        DROP TABLE IF EXISTS scene_items;
        DROP TABLE IF EXISTS scene_images;

        CREATE TABLE scene_images (
            image_id TEXT PRIMARY KEY,
            image_path TEXT NOT NULL,
            timestamp TEXT,
            area_hint TEXT,
            scene_brief TEXT,
            overall_lighting TEXT
        );

        CREATE TABLE scene_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,
            item_id TEXT,
            possible_name TEXT,
            shape TEXT,
            location_in_image TEXT,
            confidence REAL,
            FOREIGN KEY (image_id) REFERENCES scene_images(image_id) ON DELETE CASCADE
        );

        CREATE TABLE scene_uncertainty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,
            text TEXT,
            FOREIGN KEY (image_id) REFERENCES scene_images(image_id) ON DELETE CASCADE
        );

        CREATE INDEX idx_scene_items_image_id ON scene_items(image_id);
        CREATE INDEX idx_scene_items_possible_name ON scene_items(possible_name);
        CREATE INDEX idx_scene_uncertainty_image_id ON scene_uncertainty(image_id);
        """
    )


def insert_scene_observation(
    conn: sqlite3.Connection,
    obs: "SceneDescriptionObservation",
) -> None:
    conn.execute(
        """
        INSERT INTO scene_images
        (image_id, image_path, timestamp, area_hint, scene_brief, overall_lighting)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(image_id) DO UPDATE SET
            image_path = excluded.image_path,
            timestamp = excluded.timestamp,
            area_hint = excluded.area_hint,
            scene_brief = excluded.scene_brief,
            overall_lighting = excluded.overall_lighting
        """,
        (
            obs.image_id,
            obs.image_path,
            obs.timestamp,
            obs.area_hint,
            obs.scene_brief,
            obs.overall_lighting,
        ),
    )

    conn.execute("DELETE FROM scene_items WHERE image_id = ?", (obs.image_id,))
    conn.execute("DELETE FROM scene_uncertainty WHERE image_id = ?", (obs.image_id,))

    conn.executemany(
        """
        INSERT INTO scene_items
        (image_id, item_id, possible_name, shape, location_in_image, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                obs.image_id,
                item.item_id,
                item.possible_name,
                item.shape,
                item.location_in_image,
                item.confidence,
            )
            for item in obs.items
        ],
    )
    conn.executemany(
        "INSERT INTO scene_uncertainty (image_id, text) VALUES (?, ?)",
        [(obs.image_id, text) for text in obs.uncertainty],
    )


def find_scene_image_ids_by_item(
    conn: sqlite3.Connection,
    item_keyword: str | None,
    min_confidence: float = 0.0,
    limit: int = 50,
) -> list[str]:
    if item_keyword:
        rows = conn.execute(
            """
            SELECT DISTINCT image_id
            FROM scene_items
            WHERE possible_name LIKE ? COLLATE NOCASE
              AND confidence >= ?
            ORDER BY image_id
            LIMIT ?
            """,
            (f"%{item_keyword}%", min_confidence, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT image_id FROM scene_images ORDER BY image_id LIMIT ?",
            (limit,),
        ).fetchall()
    return [row["image_id"] for row in rows]


def fetch_scene_summaries(
    conn: sqlite3.Connection,
    image_ids: list[str],
) -> list[dict]:
    if not image_ids:
        return []

    placeholders = ",".join("?" for _ in image_ids)
    images = conn.execute(
        f"""
        SELECT *
        FROM scene_images
        WHERE image_id IN ({placeholders})
        ORDER BY image_id
        """,
        image_ids,
    ).fetchall()
    item_rows = conn.execute(
        f"""
        SELECT image_id, item_id, possible_name, shape, location_in_image, confidence
        FROM scene_items
        WHERE image_id IN ({placeholders})
        ORDER BY image_id, id
        """,
        image_ids,
    ).fetchall()
    uncertainty_rows = conn.execute(
        f"""
        SELECT image_id, text
        FROM scene_uncertainty
        WHERE image_id IN ({placeholders})
        ORDER BY image_id, id
        """,
        image_ids,
    ).fetchall()

    items_by_image: dict[str, list[dict]] = {}
    for row in item_rows:
        item = dict(row)
        image_id = item.pop("image_id")
        items_by_image.setdefault(image_id, []).append(item)

    uncertainty_by_image: dict[str, list[str]] = {}
    for row in uncertainty_rows:
        uncertainty_by_image.setdefault(row["image_id"], []).append(row["text"])

    return [
        {
            "image_id": image["image_id"],
            "image_path": image["image_path"],
            "timestamp": image["timestamp"],
            "area_hint": image["area_hint"],
            "scene_brief": image["scene_brief"],
            "overall_lighting": image["overall_lighting"],
            "items": items_by_image.get(image["image_id"], []),
            "uncertainty": uncertainty_by_image.get(image["image_id"], []),
        }
        for image in images
    ]
