from datetime import datetime, timedelta, timezone

import main
from app.service import PollResult


def test_run_once_calls_runner(monkeypatch):
    called = {"count": 0}

    class FakeRunner:
        def run_once(self):
            called["count"] += 1

        def serve(self):
            raise AssertionError("serve should not be called")

    monkeypatch.setattr(main, "build_runner", lambda: FakeRunner())

    exit_code = main.main(["run-once"])

    assert exit_code == 0
    assert called["count"] == 1


def test_should_send_heartbeat_when_no_previous_timestamp():
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)

    assert main.should_send_heartbeat(None, heartbeat_interval_hours=6, now=now) is True


def test_should_send_heartbeat_when_interval_not_reached():
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    last = now - timedelta(hours=2)

    assert main.should_send_heartbeat(last.isoformat(), heartbeat_interval_hours=6, now=now) is False


def test_build_heartbeat_text_summarizes_poll_results():
    results = [
        PollResult(creator_name='A', new_video_ids=['1', '2'], sent_count=2),
        PollResult(creator_name='B', new_video_ids=[], sent_count=0, error='timeout'),
    ]

    text = main.build_heartbeat_text(results, creator_count=2)

    assert '健康心跳' in text
    assert '监控博主数：2' in text
    assert '本轮新增视频：2' in text
    assert '失败博主：B' in text


def test_build_startup_text_contains_core_runtime_info():
    text = main.build_startup_text(creator_count=5, poll_interval_minutes=30, heartbeat_enabled=True, heartbeat_interval_hours=6)

    assert '服务启动成功' in text
    assert '监控博主数：5' in text
    assert '轮询间隔：30 分钟' in text
    assert '健康心跳：开启（每 6 小时）' in text
