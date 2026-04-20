from app.db import Database
from app.models import VideoRecord


def test_database_creates_schema(tmp_path):
    db = Database(tmp_path / "app.db")
    db.initialize()

    assert (tmp_path / "app.db").exists()


def test_mark_and_detect_seen_video(tmp_path):
    db = Database(tmp_path / "app.db")
    db.initialize()
    video = VideoRecord(
        creator_name="Alice",
        video_id="vid-1",
        title="new video",
        video_url="https://example.com/v/1",
    )

    assert db.has_video("vid-1") is False
    db.save_video(video, notified=False)
    assert db.has_video("vid-1") is True
