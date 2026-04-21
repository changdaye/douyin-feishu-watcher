from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class Creator:
    name: str
    profile_url: str
    enabled: bool = True


@dataclass(slots=True)
class VideoRecord:
    creator_name: str
    video_id: str
    title: str
    video_url: str
    publish_time: Optional[datetime] = None
    cover_url: Optional[str] = None
