from __future__ import annotations

import json
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.models import VideoRecord


def parse_creator_videos(html: str, *, creator_name: str) -> list[VideoRecord]:
    soup = BeautifulSoup(html, "lxml")
    script = soup.select_one("script#RENDER_DATA")
    if script is None or not script.text.strip():
        return []

    payload = json.loads(script.text)
    videos: list[VideoRecord] = []
    for item in payload.get("aweme_list", []):
        video_id = item.get("aweme_id")
        if not video_id:
            continue
        cover_urls = item.get("video", {}).get("cover", {}).get("url_list", [])
        publish_time = datetime.fromtimestamp(item.get("create_time", 0), tz=timezone.utc)
        videos.append(
            VideoRecord(
                creator_name=creator_name,
                video_id=video_id,
                title=item.get("desc") or f"{creator_name} 发布了新视频",
                video_url=item.get("share_url") or f"https://www.douyin.com/video/{video_id}",
                publish_time=publish_time,
                cover_url=cover_urls[0] if cover_urls else None,
            )
        )
    videos.sort(key=lambda video: video.publish_time or datetime.fromtimestamp(0, tz=timezone.utc), reverse=True)
    return videos
