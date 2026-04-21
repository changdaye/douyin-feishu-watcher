from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import load_creators, load_settings
from app.db import Database
from app.fetcher import CreatorPageFetcher
from app.notifier import FeishuNotifier
from app.parser import parse_creator_videos
from app.scheduler import SchedulerRunner
from app.service import PollResult, PollService


def should_send_heartbeat(last_heartbeat_at: Optional[str], *, heartbeat_interval_hours: int, now: Optional[datetime] = None) -> bool:
    if not last_heartbeat_at:
        return True
    current = now or datetime.now(timezone.utc)
    previous = datetime.fromisoformat(last_heartbeat_at)
    return current - previous >= timedelta(hours=heartbeat_interval_hours)


def build_heartbeat_text(results: list[PollResult], *, creator_count: int) -> str:
    total_new = sum(result.sent_count for result in results)
    failed = [result.creator_name for result in results if result.error]
    failed_text = '、'.join(failed) if failed else '无'
    return (
        '健康心跳\n'
        f'监控博主数：{creator_count}\n'
        f'本轮新增视频：{total_new}\n'
        f'失败博主：{failed_text}'
    )


def build_startup_text(*, creator_count: int, poll_interval_minutes: int, heartbeat_enabled: bool, heartbeat_interval_hours: int) -> str:
    heartbeat_text = f'开启（每 {heartbeat_interval_hours} 小时）' if heartbeat_enabled else '关闭'
    return (
        '服务启动成功\n'
        f'监控博主数：{creator_count}\n'
        f'轮询间隔：{poll_interval_minutes} 分钟\n'
        f'健康心跳：{heartbeat_text}'
    )


def build_job() -> Callable[[], None]:
    settings = load_settings()
    creators = load_creators(settings.creators_file)
    if not settings.feishu_webhook_url:
        raise ValueError('FEISHU_WEBHOOK_URL is required')

    database = Database(settings.sqlite_path)
    database.initialize()
    fetcher = CreatorPageFetcher(
        timeout_seconds=settings.request_timeout_seconds,
        douyin_cookie=settings.douyin_cookie,
    )
    notifier = FeishuNotifier(
        webhook_url=settings.feishu_webhook_url,
        timeout_seconds=settings.request_timeout_seconds,
        bot_secret=settings.feishu_bot_secret,
    )
    service = PollService(
        fetcher=fetcher,
        parser=parse_creator_videos,
        database=database,
        notifier=notifier,
        failure_alert_threshold=settings.failure_alert_threshold,
    )

    def job() -> None:
        results = service.poll_all(creators)
        total_new = sum(result.sent_count for result in results)
        failed = [result.creator_name for result in results if result.error]
        print(f"checked={len(results)} new_videos={total_new} failed={','.join(failed) if failed else 'none'}")

        if settings.heartbeat_enabled:
            last_heartbeat_at = database.get_state('last_heartbeat_at')
            now = datetime.now(timezone.utc)
            if should_send_heartbeat(last_heartbeat_at, heartbeat_interval_hours=settings.heartbeat_interval_hours, now=now):
                notifier.send_heartbeat(build_heartbeat_text(results, creator_count=len(creators)))
                database.set_state('last_heartbeat_at', now.isoformat())

    return job


def build_startup_callback():
    settings = load_settings()
    creators = load_creators(settings.creators_file)
    if not settings.feishu_webhook_url or not settings.startup_notification_enabled:
        return None
    notifier = FeishuNotifier(
        webhook_url=settings.feishu_webhook_url,
        timeout_seconds=settings.request_timeout_seconds,
        bot_secret=settings.feishu_bot_secret,
    )

    def startup_callback() -> None:
        notifier.send_startup(
            build_startup_text(
                creator_count=len(creators),
                poll_interval_minutes=settings.poll_interval_minutes,
                heartbeat_enabled=settings.heartbeat_enabled,
                heartbeat_interval_hours=settings.heartbeat_interval_hours,
            )
        )

    return startup_callback


def build_runner() -> SchedulerRunner:
    settings = load_settings()
    return SchedulerRunner(
        interval_minutes=settings.poll_interval_minutes,
        job=build_job(),
        startup_callback=build_startup_callback(),
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['run-once', 'serve'])
    args = parser.parse_args(argv)

    runner = build_runner()
    if args.mode == 'run-once':
        runner.run_once()
        return 0

    runner.serve()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
