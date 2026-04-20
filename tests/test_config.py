import json

from app.config import load_creators, load_settings


def test_load_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("CREATORS_FILE", str(tmp_path / "creators.json"))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "app.db"))

    settings = load_settings()

    assert settings.poll_interval_minutes == 30
    assert settings.request_timeout_seconds == 15
    assert settings.failure_alert_threshold == 3


def test_load_creators_only_enabled_items(tmp_path):
    creators_file = tmp_path / "creators.json"
    creators_file.write_text(
        json.dumps([
            {"name": "A", "profile_url": "https://example.com/a", "enabled": True},
            {"name": "B", "profile_url": "https://example.com/b", "enabled": False}
        ]),
        encoding="utf-8",
    )

    creators = load_creators(creators_file)

    assert [creator.name for creator in creators] == ["A"]
