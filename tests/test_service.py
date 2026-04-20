from app.models import Creator, VideoRecord
from app.service import PollService


class FakeFetcher:
    def fetch(self, profile_url: str) -> str:
        return profile_url


class FakeParser:
    def __call__(self, html: str, *, creator_name: str):
        return [
            VideoRecord(creator_name=creator_name, video_id="new-1", title="new", video_url="https://example.com/new"),
            VideoRecord(creator_name=creator_name, video_id="old-1", title="old", video_url="https://example.com/old"),
        ]


class FakeDB:
    def __init__(self):
        self.saved = []

    def has_video(self, video_id: str) -> bool:
        return video_id == "old-1"

    def save_video(self, video, *, notified: bool) -> None:
        self.saved.append((video.video_id, notified))


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send_video(self, video):
        self.sent.append(video.video_id)


def test_poll_service_only_notifies_for_unseen_videos():
    service = PollService(
        fetcher=FakeFetcher(),
        parser=FakeParser(),
        database=FakeDB(),
        notifier=FakeNotifier(),
    )
    creator = Creator(name="Alice", profile_url="https://example.com/alice")

    result = service.poll_creator(creator)

    assert result.new_video_ids == ["new-1"]
    assert result.sent_count == 1
