from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from app.models import Creator


@dataclass(slots=True)
class PollResult:
    creator_name: str
    new_video_ids: list[str]
    sent_count: int
    error: Optional[str] = None
    baseline_initialized: bool = False


class PollService:
    def __init__(self, *, fetcher, parser, database, notifier, failure_alert_threshold: int) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.database = database
        self.notifier = notifier
        self.failure_alert_threshold = failure_alert_threshold

    def poll_creator(self, creator: Creator) -> PollResult:
        creator_key = creator.profile_url
        try:
            html = self.fetcher.fetch(creator.profile_url)
            videos = self.parser(html, creator_name=creator.name)
            self.database.reset_failures(creator_key)

            if not self.database.has_any_videos_for_creator(creator.name):
                for video in videos:
                    self.database.save_video(video, notified=False)
                return PollResult(
                    creator_name=creator.name,
                    new_video_ids=[],
                    sent_count=0,
                    baseline_initialized=True,
                )

            new_ids: list[str] = []
            for video in videos:
                if self.database.has_video(video.video_id):
                    continue
                self.notifier.send_video(video)
                self.database.save_video(video, notified=True)
                new_ids.append(video.video_id)

            return PollResult(
                creator_name=creator.name,
                new_video_ids=new_ids,
                sent_count=len(new_ids),
            )
        except Exception as exc:
            failure_count = self.database.record_failure(creator_key)
            if failure_count >= self.failure_alert_threshold:
                self.notifier.send_alert(
                    f"监控异常提醒\n博主：{creator.name}\n链接：{creator.profile_url}\n连续失败次数：{failure_count}\n最近错误：{exc}"
                )
            return PollResult(
                creator_name=creator.name,
                new_video_ids=[],
                sent_count=0,
                error=str(exc),
            )

    def poll_all(self, creators: Iterable[Creator]) -> list[PollResult]:
        return [self.poll_creator(creator) for creator in creators]
