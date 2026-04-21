from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.models import Creator


@dataclass(slots=True)
class AppConfig:
    feishu_webhook_url: str | None
    feishu_bot_secret: str | None
    douyin_cookie: str | None
    creators_file: Path
    sqlite_path: Path
    poll_interval_minutes: int = 30
    request_timeout_seconds: int = 15
    failure_alert_threshold: int = 3


def _load_dotenv_defaults(dotenv_path: Path = Path('.env')) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _getenv(name: str, default: str | None = None) -> str | None:
    if name in os.environ:
        return os.environ[name]
    dotenv_values = _load_dotenv_defaults()
    if name in dotenv_values:
        return dotenv_values[name]
    return default


def load_settings() -> AppConfig:
    return AppConfig(
        feishu_webhook_url=_getenv('FEISHU_WEBHOOK_URL'),
        feishu_bot_secret=_getenv('FEISHU_BOT_SECRET'),
        douyin_cookie=_getenv('DOUYIN_COOKIE'),
        creators_file=Path(_getenv('CREATORS_FILE', 'creators.json') or 'creators.json'),
        sqlite_path=Path(_getenv('SQLITE_PATH', 'data/app.db') or 'data/app.db'),
        poll_interval_minutes=int(_getenv('POLL_INTERVAL_MINUTES', '30') or '30'),
        request_timeout_seconds=int(_getenv('REQUEST_TIMEOUT_SECONDS', '15') or '15'),
        failure_alert_threshold=int(_getenv('FAILURE_ALERT_THRESHOLD', '3') or '3'),
    )


def load_creators(path: Path) -> list[Creator]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    creators = [
        Creator(
            name=item['name'],
            profile_url=item['profile_url'],
            enabled=item.get('enabled', True),
        )
        for item in payload
    ]
    return [creator for creator in creators if creator.enabled]
