from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS creator_failures (
                    creator_key TEXT PRIMARY KEY,
                    failure_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    state_key TEXT PRIMARY KEY,
                    state_value TEXT
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

    def has_any_videos_for_creator(self, creator_name: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM videos WHERE creator_name = ? LIMIT 1",
                (creator_name,),
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
                    int(notified),
                    'sent' if notified else 'pending',
                ),
            )

    def get_failure_count(self, creator_key: str) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT failure_count FROM creator_failures WHERE creator_key = ?",
                (creator_key,),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_failure(self, creator_key: str) -> int:
        new_value = self.get_failure_count(creator_key) + 1
        with self.connect() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO creator_failures (creator_key, failure_count) VALUES (?, ?)',
                (creator_key, new_value),
            )
        return new_value

    def reset_failures(self, creator_key: str) -> None:
        with self.connect() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO creator_failures (creator_key, failure_count) VALUES (?, 0)',
                (creator_key,),
            )

    def get_state(self, key: str) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                'SELECT state_value FROM app_state WHERE state_key = ?',
                (key,),
            ).fetchone()
        return row[0] if row else None

    def set_state(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO app_state (state_key, state_value) VALUES (?, ?)',
                (key, value),
            )
