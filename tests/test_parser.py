from pathlib import Path

from app.parser import parse_creator_videos


def test_parse_creator_videos_extracts_latest_items():
    html = Path("tests/fixtures/douyin_creator_page.html").read_text(encoding="utf-8")

    videos = parse_creator_videos(html, creator_name="Alice")

    assert videos[0].video_id == "7480000000000000001"
    assert videos[0].title == "春天的第一条短片"
    assert videos[0].video_url.startswith("https://www.douyin.com/video/")
