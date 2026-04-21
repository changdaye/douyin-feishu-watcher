from __future__ import annotations

import base64
import copy
import hashlib
import hmac
from datetime import datetime
from typing import Optional

import httpx

from app.models import VideoRecord


def _format_publish_time(value: Optional[datetime]) -> str:
    if value is None:
        return "未知"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _make_sign(secret: str, timestamp: int) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def enrich_payload_with_signature(payload: dict, *, secret: str, timestamp: Optional[int] = None) -> dict:
    ts = int(datetime.now().timestamp()) if timestamp is None else timestamp
    enriched = copy.deepcopy(payload)
    enriched["timestamp"] = str(ts)
    enriched["sign"] = _make_sign(secret, ts)
    return enriched


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
    def __init__(self, *, webhook_url: str, timeout_seconds: int, bot_secret: Optional[str] = None) -> None:
        self.webhook_url = webhook_url
        self.bot_secret = bot_secret
        self.client = httpx.Client(timeout=timeout_seconds)

    def _wrap_payload(self, payload: dict) -> dict:
        if not self.bot_secret:
            return payload
        return enrich_payload_with_signature(payload, secret=self.bot_secret)

    def _post(self, payload: dict) -> httpx.Response:
        response = self.client.post(self.webhook_url, json=self._wrap_payload(payload))
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            return response
        if data.get("code") not in (None, 0):
            raise RuntimeError(data.get("msg") or f"Feishu bot error: {data['code']}")
        return response

    def send_video(self, video: VideoRecord) -> None:
        try:
            self._post(build_card_payload(video))
        except Exception:
            self._post(build_text_payload(video))

    def send_alert(self, text: str) -> None:
        self._post({"msg_type": "text", "content": {"text": text}})
