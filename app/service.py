from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models import Creator


@dataclass(slots=True)
class PollResult:
    creator_name: str
    new_video_ids: list[str]
    sent_count: int
    error: str | None = None


class PollService:
    def __init__(self, *, fetcher, parser, database, notifier) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.database = database
        self.notifier = notifier

    def poll_creator(self, creator: Creator) -> PollResult:
        try:
            html = self.fetcher.fetch(creator.profile_url)
            videos = self.parser(html, creator_name=creator.name)
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
        except Exception as exc:  # pragma: no cover - covered indirectly via behavior
            return PollResult(
                creator_name=creator.name,
                new_video_ids=[],
                sent_count=0,
                error=str(exc),
            )

    def poll_all(self, creators: Iterable[Creator]) -> list[PollResult]:
        return [self.poll_creator(creator) for creator in creators]
