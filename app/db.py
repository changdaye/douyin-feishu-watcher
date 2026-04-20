from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import VideoRecord


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    creator_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    publish_time TEXT,
                    cover_url TEXT,
                    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notified_at TEXT,
                    notify_status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )

    def has_video(self, video_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM videos WHERE video_id = ? LIMIT 1",
                (video_id,),
            ).fetchone()
        return row is not None

    def save_video(self, video: VideoRecord, *, notified: bool) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO videos (
                    video_id, creator_name, title, video_url, publish_time,
                    cover_url, notified_at, notify_status
                ) VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END, ?)
                """,
                (
                    video.video_id,
                    video.creator_name,
                    video.title,
                    video.video_url,
                    video.publish_time.isoformat() if video.publish_time else None,
                    video.cover_url,
                    notified,
                    "sent" if notified else "pending",
                ),
            )
