import json

from app.config import load_creators, load_settings


def test_load_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("FEISHU_BOT_SECRET", raising=False)
    monkeypatch.delenv("DOUYIN_COOKIE", raising=False)
    monkeypatch.delenv("APP_CONFIG_JSON", raising=False)
    monkeypatch.setenv("CREATORS_FILE", str(tmp_path / "creators.json"))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "app.db"))

    settings = load_settings()

    assert settings.poll_interval_minutes == 30
    assert settings.request_timeout_seconds == 15
    assert settings.failure_alert_threshold == 3
    assert settings.feishu_bot_secret is None
    assert settings.douyin_cookie is None
    assert settings.heartbeat_enabled is True
    assert settings.heartbeat_interval_hours == 6
    assert settings.startup_notification_enabled is True


def test_load_settings_reads_local_json_file(tmp_path, monkeypatch):
    config_file = tmp_path / 'local.runtime.json'
    config_file.write_text(
        json.dumps(
            {
                'feishu_webhook_url': 'https://open.feishu.cn/open-apis/bot/v2/hook/test-json',
                'feishu_bot_secret': 'json-secret',
                'douyin_cookie': 'sessionid=json-cookie',
                'creators_file': 'creators.local.json',
                'sqlite_path': 'state/app.db',
                'poll_interval_minutes': 45,
                'request_timeout_seconds': 21,
                'failure_alert_threshold': 5,
                'heartbeat_enabled': False,
                'heartbeat_interval_hours': 12,
                'startup_notification_enabled': False,
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('FEISHU_WEBHOOK_URL', raising=False)
    monkeypatch.delenv('FEISHU_BOT_SECRET', raising=False)
    monkeypatch.delenv('DOUYIN_COOKIE', raising=False)
    monkeypatch.delenv('APP_CONFIG_JSON', raising=False)

    settings = load_settings()

    assert settings.feishu_webhook_url == 'https://open.feishu.cn/open-apis/bot/v2/hook/test-json'
    assert settings.feishu_bot_secret == 'json-secret'
    assert settings.douyin_cookie == 'sessionid=json-cookie'
    assert str(settings.creators_file) == 'creators.local.json'
    assert str(settings.sqlite_path) == 'state/app.db'
    assert settings.poll_interval_minutes == 45
    assert settings.request_timeout_seconds == 21
    assert settings.failure_alert_threshold == 5
    assert settings.heartbeat_enabled is False
    assert settings.heartbeat_interval_hours == 12
    assert settings.startup_notification_enabled is False


def test_load_settings_reads_local_env_file_when_json_missing(tmp_path, monkeypatch):
    env_file = tmp_path / '.env'
    env_file.write_text(
        'FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/test\n'
        'FEISHU_BOT_SECRET=secret-value\n'
        'DOUYIN_COOKIE=sessionid=test-cookie\n'
        'REQUEST_TIMEOUT_SECONDS=21\n',
        encoding='utf-8',
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('FEISHU_WEBHOOK_URL', raising=False)
    monkeypatch.delenv('FEISHU_BOT_SECRET', raising=False)
    monkeypatch.delenv('DOUYIN_COOKIE', raising=False)
    monkeypatch.delenv('REQUEST_TIMEOUT_SECONDS', raising=False)
    monkeypatch.delenv('APP_CONFIG_JSON', raising=False)

    settings = load_settings()

    assert settings.feishu_webhook_url == 'https://open.feishu.cn/open-apis/bot/v2/hook/test'
    assert settings.feishu_bot_secret == 'secret-value'
    assert settings.douyin_cookie == 'sessionid=test-cookie'
    assert settings.request_timeout_seconds == 21


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
