from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Optional

from app.config import load_creators, load_settings
from app.db import Database
from app.fetcher import CreatorPageFetcher
from app.notifier import FeishuNotifier
from app.parser import parse_creator_videos
from app.scheduler import SchedulerRunner
from app.service import PollService


def build_job() -> Callable[[], None]:
    settings = load_settings()
    creators = load_creators(settings.creators_file)
    if not settings.feishu_webhook_url:
        raise ValueError("FEISHU_WEBHOOK_URL is required")

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

    return job


def build_runner() -> SchedulerRunner:
    settings = load_settings()
    return SchedulerRunner(interval_minutes=settings.poll_interval_minutes, job=build_job())


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["run-once", "serve"])
    args = parser.parse_args(argv)

    runner = build_runner()
    if args.mode == "run-once":
        runner.run_once()
        return 0

    runner.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
