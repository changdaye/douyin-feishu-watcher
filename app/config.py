from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from app.models import Creator


@dataclass(slots=True)
class AppConfig:
    feishu_webhook_url: Optional[str]
    feishu_bot_secret: Optional[str]
    douyin_cookie: Optional[str]
    creators_file: Path
    sqlite_path: Path
    poll_interval_minutes: int = 30
    request_timeout_seconds: int = 15
    failure_alert_threshold: int = 3
    heartbeat_enabled: bool = True
    heartbeat_interval_hours: int = 6
    startup_notification_enabled: bool = True


DEFAULT_JSON_CONFIG_CANDIDATES = [
    'local.runtime.json',
    'runtime.local.json',
    'config.local.json',
]


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


def _load_json_defaults() -> dict[str, object]:
    configured_path = os.getenv('APP_CONFIG_JSON')
    candidates = [configured_path] if configured_path else DEFAULT_JSON_CONFIG_CANDIDATES
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError(f'JSON config must be an object: {path}')
        return data
    return {}


def _get_config_value(name: str, default: Optional[str] = None) -> Any:
    if name in os.environ:
        return os.environ[name]

    json_values = _load_json_defaults()
    json_key = name.lower()
    if json_key in json_values:
        return json_values[json_key]

    dotenv_values = _load_dotenv_defaults()
    if name in dotenv_values:
        return dotenv_values[name]

    return default


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {'0', 'false', 'no', 'off'}


def load_settings() -> AppConfig:
    return AppConfig(
        feishu_webhook_url=_get_config_value('FEISHU_WEBHOOK_URL'),
        feishu_bot_secret=_get_config_value('FEISHU_BOT_SECRET'),
        douyin_cookie=_get_config_value('DOUYIN_COOKIE'),
        creators_file=Path(str(_get_config_value('CREATORS_FILE', 'creators.json') or 'creators.json')),
        sqlite_path=Path(str(_get_config_value('SQLITE_PATH', 'data/app.db') or 'data/app.db')),
        poll_interval_minutes=int(str(_get_config_value('POLL_INTERVAL_MINUTES', '30') or '30')),
        request_timeout_seconds=int(str(_get_config_value('REQUEST_TIMEOUT_SECONDS', '15') or '15')),
        failure_alert_threshold=int(str(_get_config_value('FAILURE_ALERT_THRESHOLD', '3') or '3')),
        heartbeat_enabled=_to_bool(_get_config_value('HEARTBEAT_ENABLED', 'true'), True),
        heartbeat_interval_hours=int(str(_get_config_value('HEARTBEAT_INTERVAL_HOURS', '6') or '6')),
        startup_notification_enabled=_to_bool(_get_config_value('STARTUP_NOTIFICATION_ENABLED', 'true'), True),
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
