from __future__ import annotations

from datetime import datetime

import httpx

from app.models import VideoRecord


def _format_publish_time(value: datetime | None) -> str:
    if value is None:
        return "未知"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def build_card_payload(video: VideoRecord) -> dict:
    elements = [
        {"tag": "markdown", "content": f"**博主**：{video.creator_name}"},
        {"tag": "markdown", "content": f"**标题**：{video.title}"},
        {"tag": "markdown", "content": f"**发布时间**：{_format_publish_time(video.publish_time)}"},
        {"tag": "markdown", "content": f"**链接**：[打开抖音]({video.video_url})"},
    ]
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "抖音更新提醒"}},
            "elements": elements,
        },
    }


def build_text_payload(video: VideoRecord) -> dict:
    return {
        "msg_type": "text",
        "content": {
            "text": (
                "抖音更新提醒\n"
                f"博主：{video.creator_name}\n"
                f"标题：{video.title}\n"
                f"发布时间：{_format_publish_time(video.publish_time)}\n"
                f"链接：{video.video_url}"
            )
        },
    }


class FeishuNotifier:
    def __init__(self, *, webhook_url: str, timeout_seconds: int) -> None:
        self.webhook_url = webhook_url
        self.client = httpx.Client(timeout=timeout_seconds)

    def send_video(self, video: VideoRecord) -> None:
        response = self.client.post(self.webhook_url, json=build_card_payload(video))
        if response.is_success:
            return
        fallback = self.client.post(self.webhook_url, json=build_text_payload(video))
        fallback.raise_for_status()
