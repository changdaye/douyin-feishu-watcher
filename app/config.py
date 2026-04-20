from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.models import Creator


@dataclass(slots=True)
class AppConfig:
    feishu_webhook_url: str | None
    creators_file: Path
    sqlite_path: Path
    poll_interval_minutes: int = 30
    request_timeout_seconds: int = 15
    failure_alert_threshold: int = 3


def load_settings() -> AppConfig:
    return AppConfig(
        feishu_webhook_url=os.getenv("FEISHU_WEBHOOK_URL"),
        creators_file=Path(os.getenv("CREATORS_FILE", "creators.json")),
        sqlite_path=Path(os.getenv("SQLITE_PATH", "data/app.db")),
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "30")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        failure_alert_threshold=int(os.getenv("FAILURE_ALERT_THRESHOLD", "3")),
    )


def load_creators(path: Path) -> list[Creator]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    creators = [
        Creator(
            name=item["name"],
            profile_url=item["profile_url"],
            enabled=item.get("enabled", True),
        )
        for item in payload
    ]
    return [creator for creator in creators if creator.enabled]
