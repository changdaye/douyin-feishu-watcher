from app.models import Creator, VideoRecord
from app.service import PollService


class FakeFetcher:
    def fetch(self, profile_url: str) -> str:
        return profile_url


class FakeFailingFetcher:
    def fetch(self, profile_url: str) -> str:
        raise RuntimeError("boom")


class FakeParser:
    def __call__(self, html: str, *, creator_name: str):
        return [
            VideoRecord(creator_name=creator_name, video_id="new-1", title="new", video_url="https://example.com/new"),
            VideoRecord(creator_name=creator_name, video_id="old-1", title="old", video_url="https://example.com/old"),
        ]


class FakeDB:
    def __init__(self, *, has_existing_creator: bool = True):
        self.saved = []
        self.failure_counts = {}
        self.has_existing_creator = has_existing_creator

    def has_video(self, video_id: str) -> bool:
        return video_id == "old-1"

    def save_video(self, video, *, notified: bool) -> None:
        self.saved.append((video.video_id, notified))

    def has_any_videos_for_creator(self, creator_name: str) -> bool:
        return self.has_existing_creator

    def record_failure(self, creator_key: str) -> int:
        value = self.failure_counts.get(creator_key, 0) + 1
        self.failure_counts[creator_key] = value
        return value

    def reset_failures(self, creator_key: str) -> None:
        self.failure_counts[creator_key] = 0


class FakeNotifier:
    def __init__(self):
        self.sent = []
        self.alerts = []

    def send_video(self, video):
        self.sent.append(video.video_id)

    def send_alert(self, text: str):
        self.alerts.append(text)


def test_poll_service_only_notifies_for_unseen_videos():
    service = PollService(
        fetcher=FakeFetcher(),
        parser=FakeParser(),
        database=FakeDB(),
        notifier=FakeNotifier(),
        failure_alert_threshold=3,
    )
    creator = Creator(name="Alice", profile_url="https://example.com/alice")

    result = service.poll_creator(creator)

    assert result.new_video_ids == ["new-1"]
    assert result.sent_count == 1


def test_first_poll_builds_baseline_without_notifications():
    db = FakeDB(has_existing_creator=False)
    notifier = FakeNotifier()
    service = PollService(
        fetcher=FakeFetcher(),
        parser=FakeParser(),
        database=db,
        notifier=notifier,
        failure_alert_threshold=3,
    )

    result = service.poll_creator(Creator(name="Alice", profile_url="https://example.com/alice"))

    assert result.sent_count == 0
    assert notifier.sent == []
    assert db.saved == [("new-1", False), ("old-1", False)]


def test_repeated_failures_trigger_alert_after_threshold():
    db = FakeDB()
    notifier = FakeNotifier()
    service = PollService(
        fetcher=FakeFailingFetcher(),
        parser=FakeParser(),
        database=db,
        notifier=notifier,
        failure_alert_threshold=2,
    )
    creator = Creator(name="Alice", profile_url="https://example.com/alice")

    first = service.poll_creator(creator)
    second = service.poll_creator(creator)

    assert first.error == "boom"
    assert second.error == "boom"
    assert len(notifier.alerts) == 1
    assert "Alice" in notifier.alerts[0]
