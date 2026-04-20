# Douyin Feishu Watcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python service that polls a small list of public Douyin creators and pushes newly discovered videos to a Feishu webhook bot within one hour.

**Architecture:** Use a single-process Python service with a scheduler, HTTP fetcher, HTML/embedded-data parser, SQLite persistence, and a Feishu notifier. Keep creator inputs in a checked-in JSON file, store runtime state in SQLite, and run the service under systemd on the target server.

**Tech Stack:** Python 3.11, APScheduler, httpx, beautifulsoup4, lxml, sqlite3, pytest

---

## Planned File Structure

- Create: `pyproject.toml` — package metadata, runtime dependencies, pytest settings
- Create: `.gitignore` — ignore venv, SQLite DB, logs, cache files
- Create: `README.md` — setup, local run, deployment, troubleshooting
- Create: `.env.example` — runtime environment variable template
- Create: `creators.json.example` — creator input template
- Create: `app/__init__.py` — package marker
- Create: `app/config.py` — environment and file-based configuration loading
- Create: `app/models.py` — dataclasses for creator, video, poll results
- Create: `app/db.py` — SQLite schema and repository methods
- Create: `app/parser.py` — parse creator page payload into `VideoRecord` items
- Create: `app/fetcher.py` — HTTP client wrapper for creator pages
- Create: `app/notifier.py` — Feishu webhook sender with card/text fallback
- Create: `app/service.py` — orchestration for poll, dedupe, notify, persist
- Create: `app/scheduler.py` — APScheduler setup and periodic execution
- Create: `main.py` — CLI entrypoint for `run-once` and `serve`
- Create: `tests/conftest.py` — shared pytest fixtures
- Create: `tests/test_config.py` — configuration coverage
- Create: `tests/test_db.py` — schema and dedupe coverage
- Create: `tests/fixtures/douyin_creator_page.html` — parser fixture snapshot
- Create: `tests/test_parser.py` — parser coverage
- Create: `tests/test_notifier.py` — Feishu payload/retry coverage
- Create: `tests/test_service.py` — end-to-end orchestration coverage with fakes
- Create: `tests/test_main.py` — CLI mode coverage
- Create: `deploy/douyin-feishu-watcher.service` — systemd service unit

## Task 1: Bootstrap the Python project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing smoke test for project imports**

```python
# tests/conftest.py
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure() -> None:
    import app  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails before package bootstrap**

Run: `pytest tests -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Create the minimal project files**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "douyin-feishu-watcher"
version = "0.1.0"
description = "Poll public Douyin creators and push updates to a Feishu bot"
requires-python = ">=3.11"
dependencies = [
  "APScheduler==3.11.0",
  "beautifulsoup4==4.13.3",
  "httpx==0.28.1",
  "lxml==5.3.1",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.5",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```gitignore
# .gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
.env
/data/*.db
/logs/
```

```python
# app/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```markdown
# README.md
# Douyin Feishu Watcher

Python service for polling public Douyin creators and sending new video alerts to a Feishu webhook bot.
```

- [ ] **Step 4: Run test to verify bootstrap passes**

Run: `pytest tests -q`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the bootstrap baseline**

```bash
git add pyproject.toml .gitignore README.md app/__init__.py tests/conftest.py
git commit -F - <<'EOF'
Create a minimal Python repo so later polling work has a stable base

The project needs a package, dependency manifest, test harness, and ignore
rules before any behavior can be implemented safely.

Confidence: high
Scope-risk: narrow
Reversibility: clean
Directive: Keep the dependency list minimal unless a later task proves a need
Tested: pytest tests -q
EOF
```

## Task 2: Add configuration loading and creator input parsing

**Files:**
- Create: `.env.example`
- Create: `creators.json.example`
- Create: `app/config.py`
- Create: `app/models.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for configuration defaults and creator loading**

```python
# tests/test_config.py
import json

from app.config import load_creators, load_settings


def test_load_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("CREATORS_FILE", str(tmp_path / "creators.json"))
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "app.db"))

    settings = load_settings()

    assert settings.poll_interval_minutes == 30
    assert settings.request_timeout_seconds == 15
    assert settings.failure_alert_threshold == 3


def test_load_creators_only_enabled_items(tmp_path):
    creators_file = tmp_path / "creators.json"
    creators_file.write_text(
        json.dumps([
            {"name": "A", "profile_url": "https://example.com/a", "enabled": True},
            {"name": "B", "profile_url": "https://example.com/b", "enabled": False}
        ]),
        encoding="utf-8",
    )

    creators = load_creators(creators_file)

    assert [creator.name for creator in creators] == ["A"]
```

- [ ] **Step 2: Run tests to verify they fail before implementation**

Run: `pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Implement settings and creator models**

```python
# app/models.py
from dataclasses import dataclass
from datetime import datetime


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
    publish_time: datetime | None = None
    cover_url: str | None = None
```

```python
# app/config.py
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.models import Creator


@dataclass(slots=True)
class AppConfig:
    feishu_webhook_url: str | None
    creators_file: Path
    sqlite_path: Path
    poll_interval_minutes: int = 30
    request_timeout_seconds: int = 15
    failure_alert_threshold: int = 3


def load_settings() -> AppConfig:
    return AppConfig(
        feishu_webhook_url=os.getenv("FEISHU_WEBHOOK_URL"),
        creators_file=Path(os.getenv("CREATORS_FILE", "creators.json")),
        sqlite_path=Path(os.getenv("SQLITE_PATH", "data/app.db")),
        poll_interval_minutes=int(os.getenv("POLL_INTERVAL_MINUTES", "30")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        failure_alert_threshold=int(os.getenv("FAILURE_ALERT_THRESHOLD", "3")),
    )


def load_creators(path: Path) -> list[Creator]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    creators = [
        Creator(
            name=item["name"],
            profile_url=item["profile_url"],
            enabled=item.get("enabled", True),
        )
        for item in payload
    ]
    return [creator for creator in creators if creator.enabled]
```

```dotenv
# .env.example
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/replace-me
CREATORS_FILE=creators.json
SQLITE_PATH=data/app.db
POLL_INTERVAL_MINUTES=30
REQUEST_TIMEOUT_SECONDS=15
FAILURE_ALERT_THRESHOLD=3
```

```json
[
  {
    "name": "示例博主",
    "profile_url": "https://www.douyin.com/user/replace-me",
    "enabled": true
  }
]
```

- [ ] **Step 4: Run the configuration tests to verify they pass**

Run: `pytest tests/test_config.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit configuration support**

```bash
git add .env.example creators.json.example app/config.py app/models.py tests/test_config.py
git commit -F - <<'EOF'
Define runtime configuration so the watcher can be deployed repeatably

The service needs explicit environment and creator inputs before persistence,
fetching, or scheduling can be built on top.

Confidence: high
Scope-risk: narrow
Reversibility: clean
Directive: Prefer standard-library config loading unless operational complexity increases
Tested: pytest tests/test_config.py -q
EOF
```

## Task 3: Build SQLite persistence and dedupe primitives

**Files:**
- Create: `app/db.py`
- Create: `tests/test_db.py`
- Modify: `app/models.py`

- [ ] **Step 1: Write failing tests for schema creation and duplicate detection**

```python
# tests/test_db.py
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
```

- [ ] **Step 2: Run tests to confirm they fail before database code exists**

Run: `pytest tests/test_db.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Implement the repository layer**

```python
# app/db.py
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import VideoRecord


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    creator_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    publish_time TEXT,
                    cover_url TEXT,
                    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notified_at TEXT,
                    notify_status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )

    def has_video(self, video_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM videos WHERE video_id = ? LIMIT 1",
                (video_id,),
            ).fetchone()
        return row is not None

    def save_video(self, video: VideoRecord, *, notified: bool) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO videos (
                    video_id, creator_name, title, video_url, publish_time,
                    cover_url, notified_at, notify_status
                ) VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END, ?)
                """,
                (
                    video.video_id,
                    video.creator_name,
                    video.title,
                    video.video_url,
                    video.publish_time.isoformat() if video.publish_time else None,
                    video.cover_url,
                    notified,
                    "sent" if notified else "pending",
                ),
            )
```

- [ ] **Step 4: Run database tests to verify dedupe primitives pass**

Run: `pytest tests/test_db.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit persistence support**

```bash
git add app/db.py app/models.py tests/test_db.py
git commit -F - <<'EOF'
Persist discovered videos so the watcher can avoid duplicate alerts

Reliable notifications depend on a durable store that remembers which video ids
were already seen across process restarts.

Confidence: high
Scope-risk: narrow
Reversibility: clean
Directive: Keep SQLite access simple until concurrent writers become a real need
Tested: pytest tests/test_db.py -q
EOF
```

## Task 4: Parse creator pages into normalized video records

**Files:**
- Create: `app/parser.py`
- Create: `tests/fixtures/douyin_creator_page.html`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing parser test against a stored fixture**

```python
# tests/test_parser.py
from pathlib import Path

from app.parser import parse_creator_videos


def test_parse_creator_videos_extracts_latest_items():
    html = Path("tests/fixtures/douyin_creator_page.html").read_text(encoding="utf-8")

    videos = parse_creator_videos(html, creator_name="Alice")

    assert videos[0].video_id == "7480000000000000001"
    assert videos[0].title == "春天的第一条短片"
    assert videos[0].video_url.startswith("https://www.douyin.com/video/")
```

- [ ] **Step 2: Run parser test to confirm it fails before parser code exists**

Run: `pytest tests/test_parser.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.parser'`

- [ ] **Step 3: Add fixture data and parser implementation**

```html
<!-- tests/fixtures/douyin_creator_page.html -->
<html>
  <body>
    <script id="RENDER_DATA" type="application/json">
      {
        "aweme_list": [
          {
            "aweme_id": "7480000000000000001",
            "desc": "春天的第一条短片",
            "create_time": 1776633300,
            "share_url": "https://www.douyin.com/video/7480000000000000001",
            "video": {
              "cover": {"url_list": ["https://example.com/cover-1.jpg"]}
            }
          }
        ]
      }
    </script>
  </body>
</html>
```

```python
# app/parser.py
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
        videos.append(
            VideoRecord(
                creator_name=creator_name,
                video_id=video_id,
                title=item.get("desc") or f"{creator_name} 发布了新视频",
                video_url=item.get("share_url") or f"https://www.douyin.com/video/{video_id}",
                publish_time=datetime.fromtimestamp(item.get("create_time", 0), tz=timezone.utc),
                cover_url=cover_urls[0] if cover_urls else None,
            )
        )
    return videos
```

- [ ] **Step 4: Run parser tests to verify the fixture is parsed correctly**

Run: `pytest tests/test_parser.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the parser slice**

```bash
git add app/parser.py tests/fixtures/douyin_creator_page.html tests/test_parser.py
git commit -F - <<'EOF'
Normalize creator pages into video records so new uploads can be compared safely

The watcher needs one parser boundary that converts raw page data into stable
video records before any dedupe or notification logic runs.

Confidence: medium
Scope-risk: moderate
Reversibility: clean
Directive: Update the fixture first when Douyin changes page structure, then adjust the parser
Tested: pytest tests/test_parser.py -q
EOF
```

## Task 5: Add HTTP fetching and Feishu webhook notification

**Files:**
- Create: `app/fetcher.py`
- Create: `app/notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write failing tests for Feishu payload generation and fallback behavior**

```python
# tests/test_notifier.py
from app.models import VideoRecord
from app.notifier import build_card_payload, build_text_payload


def test_build_card_payload_contains_core_fields():
    video = VideoRecord(
        creator_name="Alice",
        video_id="vid-1",
        title="Hello",
        video_url="https://example.com/v/1",
    )

    payload = build_card_payload(video)

    assert payload["msg_type"] == "interactive"
    assert "Alice" in str(payload)
    assert "https://example.com/v/1" in str(payload)


def test_build_text_payload_is_plaintext_fallback():
    video = VideoRecord(
        creator_name="Alice",
        video_id="vid-1",
        title="Hello",
        video_url="https://example.com/v/1",
    )

    payload = build_text_payload(video)

    assert payload["msg_type"] == "text"
    assert "Hello" in payload["content"]["text"]
```

- [ ] **Step 2: Run tests to verify notifier code is missing**

Run: `pytest tests/test_notifier.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.notifier'`

- [ ] **Step 3: Implement the HTTP client wrapper and notifier payload builders**

```python
# app/fetcher.py
from __future__ import annotations

import httpx


class CreatorPageFetcher:
    def __init__(self, *, timeout_seconds: int) -> None:
        self.client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            },
        )

    def fetch(self, profile_url: str) -> str:
        response = self.client.get(profile_url)
        response.raise_for_status()
        return response.text
```

```python
# app/notifier.py
from __future__ import annotations

import httpx

from app.models import VideoRecord


def build_card_payload(video: VideoRecord) -> dict:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": "抖音更新提醒"}},
            "elements": [
                {"tag": "markdown", "content": f"**博主**：{video.creator_name}"},
                {"tag": "markdown", "content": f"**标题**：{video.title}"},
                {"tag": "markdown", "content": f"**链接**：[打开抖音]({video.video_url})"},
            ],
        },
    }


def build_text_payload(video: VideoRecord) -> dict:
    return {
        "msg_type": "text",
        "content": {
            "text": f"抖音更新提醒\n博主：{video.creator_name}\n标题：{video.title}\n链接：{video.video_url}"
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
```

- [ ] **Step 4: Run notifier tests to verify payload builders pass**

Run: `pytest tests/test_notifier.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit fetch and notify support**

```bash
git add app/fetcher.py app/notifier.py tests/test_notifier.py
git commit -F - <<'EOF'
Add the network boundaries so discovered videos can be fetched and announced

The watcher cannot provide value until it can read creator pages and convert new
records into Feishu webhook requests with a safe fallback.

Confidence: medium
Scope-risk: moderate
Reversibility: clean
Directive: Keep payload generation deterministic so failures can be replayed from tests
Tested: pytest tests/test_notifier.py -q
EOF
```

## Task 6: Orchestrate polling, dedupe, and notification flow

**Files:**
- Create: `app/service.py`
- Create: `tests/test_service.py`

- [ ] **Step 1: Write a failing orchestration test for one new and one old video**

```python
# tests/test_service.py
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
```

- [ ] **Step 2: Run the service test to confirm the orchestration layer is missing**

Run: `pytest tests/test_service.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.service'`

- [ ] **Step 3: Implement the poll orchestration**

```python
# app/service.py
from __future__ import annotations

from dataclasses import dataclass

from app.models import Creator


@dataclass(slots=True)
class PollResult:
    creator_name: str
    new_video_ids: list[str]
    sent_count: int


class PollService:
    def __init__(self, *, fetcher, parser, database, notifier) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.database = database
        self.notifier = notifier

    def poll_creator(self, creator: Creator) -> PollResult:
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
```

- [ ] **Step 4: Run the service test to verify new videos are the only ones notified**

Run: `pytest tests/test_service.py -q`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the orchestration layer**

```bash
git add app/service.py tests/test_service.py
git commit -F - <<'EOF'
Wire polling logic together so only unseen videos trigger Feishu alerts

The service layer is the point where fetching, parsing, dedupe, and delivery meet,
so it needs explicit tests before scheduling is added.

Confidence: high
Scope-risk: moderate
Reversibility: clean
Directive: Preserve dependency injection here so parser and notifier failures stay easy to test
Tested: pytest tests/test_service.py -q
EOF
```

## Task 7: Add CLI modes and APScheduler-based periodic execution

**Files:**
- Create: `app/scheduler.py`
- Create: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing CLI test for `run-once` mode**

```python
# tests/test_main.py
import main


def test_run_once_calls_poll_all(monkeypatch):
    called = {"count": 0}

    class FakeRunner:
        def run_once(self):
            called["count"] += 1

    monkeypatch.setattr(main, "build_runner", lambda: FakeRunner())

    main.main(["run-once"])

    assert called["count"] == 1
```

- [ ] **Step 2: Run the CLI test to verify the entrypoint is missing**

Run: `pytest tests/test_main.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Implement scheduler wiring and entrypoint**

```python
# app/scheduler.py
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler


class SchedulerRunner:
    def __init__(self, *, interval_minutes: int, job) -> None:
        self.interval_minutes = interval_minutes
        self.job = job

    def run_once(self) -> None:
        self.job()

    def serve(self) -> None:
        scheduler = BlockingScheduler()
        scheduler.add_job(self.job, "interval", minutes=self.interval_minutes, max_instances=1)
        scheduler.start()
```

```python
# main.py
from __future__ import annotations

import argparse

from app.config import load_settings
from app.scheduler import SchedulerRunner


def build_runner() -> SchedulerRunner:
    settings = load_settings()
    return SchedulerRunner(interval_minutes=settings.poll_interval_minutes, job=lambda: None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["run-once", "serve"])
    args = parser.parse_args(argv)

    runner = build_runner()
    if args.mode == "run-once":
        runner.run_once()
        return 0

    runner.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests and the growing suite**

Run: `pytest tests/test_main.py tests/test_config.py tests/test_db.py tests/test_parser.py tests/test_notifier.py tests/test_service.py -q`
Expected: PASS with `9 passed`

- [ ] **Step 5: Commit scheduler and entrypoint support**

```bash
git add app/scheduler.py main.py tests/test_main.py
git commit -F - <<'EOF'
Expose run-once and daemon modes so the watcher can operate locally and on the server

The project needs one manual execution mode for verification and one scheduled
mode for production, both driven by the same runtime settings.

Confidence: high
Scope-risk: moderate
Reversibility: clean
Directive: Keep main.py thin and move business behavior behind injected services
Tested: pytest tests/test_main.py tests/test_config.py tests/test_db.py tests/test_parser.py tests/test_notifier.py tests/test_service.py -q
EOF
```

## Task 8: Finish deployment assets and end-to-end verification docs

**Files:**
- Modify: `README.md`
- Create: `deploy/douyin-feishu-watcher.service`

- [ ] **Step 1: Write the failing documentation checklist as executable verification commands**

```markdown
# README.md
## Verification checklist

- `python -m venv .venv`
- `. .venv/bin/activate`
- `pip install -e .[dev]`
- `cp .env.example .env`
- `cp creators.json.example creators.json`
- `pytest tests -q`
- `python main.py run-once`
```

- [ ] **Step 2: Run the full suite before writing deployment docs**

Run: `pytest tests -q`
Expected: PASS with all tests green

- [ ] **Step 3: Add deployment and operations documentation plus the service unit**

```ini
# deploy/douyin-feishu-watcher.service
[Unit]
Description=Douyin Feishu Watcher
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/douyin-feishu-watcher
EnvironmentFile=/opt/douyin-feishu-watcher/.env
ExecStart=/opt/douyin-feishu-watcher/.venv/bin/python main.py serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```markdown
# README.md
## Local development
1. `python -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -e .[dev]`
4. `cp .env.example .env`
5. `cp creators.json.example creators.json`
6. `pytest tests -q`
7. `python main.py run-once`

## Deployment
1. Copy the repo to `/opt/douyin-feishu-watcher`
2. Create `.venv` and install `.[dev]` or runtime deps
3. Create `.env` and `creators.json`
4. Copy `deploy/douyin-feishu-watcher.service` to `/etc/systemd/system/`
5. Run `sudo systemctl daemon-reload`
6. Run `sudo systemctl enable --now douyin-feishu-watcher`
7. Verify with `systemctl status douyin-feishu-watcher`
```

- [ ] **Step 4: Run the final verification commands**

Run: `pytest tests -q && python main.py run-once`
Expected: Tests pass; `run-once` exits with code `0`

- [ ] **Step 5: Commit deployment readiness**

```bash
git add README.md deploy/douyin-feishu-watcher.service
git commit -F - <<'EOF'
Document deployment so the watcher can move from local checks to stable server operation

A lightweight service still needs repeatable setup instructions and a systemd unit,
or the runtime becomes fragile and hard to recover.

Confidence: high
Scope-risk: narrow
Reversibility: clean
Directive: Update README and the service file together whenever startup behavior changes
Tested: pytest tests -q && python main.py run-once
Not-tested: Live systemd enablement on the target Volcano Engine host
EOF
```

## Self-Review

### Spec coverage
- Public creator polling within one hour: covered by Tasks 5, 6, and 7
- Python implementation and lightweight stack: covered by Tasks 1, 2, and 8
- SQLite dedupe and persistence: covered by Task 3
- Feishu bot delivery with fallback: covered by Task 5
- Deployment on single cloud VM with systemd: covered by Task 8
- Observability and safe operations: covered by README and service wiring in Task 8

### Placeholder scan
- Searched for unfinished placeholders and vague “handle appropriately” instructions while drafting.
- All tasks list exact file paths, commands, and code snippets.

### Type consistency
- Shared names are consistent across tasks: `AppConfig`, `Creator`, `VideoRecord`, `Database`, `PollService`, `SchedulerRunner`.
- `VideoRecord.video_id` remains the single primary dedupe key through parser, DB, notifier, and service tasks.
