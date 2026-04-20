# Douyin Feishu Watcher

Python service for polling a small list of public Douyin creators and sending new video alerts to a Feishu webhook bot.

## What it does

- polls public creator pages on a fixed interval
- parses the newest videos from embedded page data
- deduplicates by `video_id` in SQLite
- sends Feishu card messages with text fallback
- supports `run-once` for manual checks and `serve` for daemon mode

## Project layout

```text
app/
  config.py
  db.py
  fetcher.py
  models.py
  notifier.py
  parser.py
  scheduler.py
  service.py
creators.json.example
main.py
deploy/douyin-feishu-watcher.service
```

## Local development

1. `python3 -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -e .[dev]`
4. `cp .env.example .env`
5. `cp creators.json.example creators.json`
6. Fill in `FEISHU_WEBHOOK_URL` and creator profile URLs
7. `pytest tests -q`
8. `python main.py run-once`

## Environment variables

- `FEISHU_WEBHOOK_URL`: Feishu bot webhook URL
- `CREATORS_FILE`: creator list JSON path, default `creators.json`
- `SQLITE_PATH`: SQLite database path, default `data/app.db`
- `POLL_INTERVAL_MINUTES`: scheduler interval, default `30`
- `REQUEST_TIMEOUT_SECONDS`: HTTP timeout, default `15`
- `FAILURE_ALERT_THRESHOLD`: reserved threshold for future alert escalation, default `3`

## Creator file format

```json
[
  {
    "name": "示例博主",
    "profile_url": "https://www.douyin.com/user/replace-me",
    "enabled": true
  }
]
```

## Deployment

1. Copy the repo to `/opt/douyin-feishu-watcher`
2. Create a virtualenv and install dependencies with `pip install -e .`
3. Create `.env` and `creators.json`
4. Copy `deploy/douyin-feishu-watcher.service` to `/etc/systemd/system/`
5. Run `sudo systemctl daemon-reload`
6. Run `sudo systemctl enable --now douyin-feishu-watcher`
7. Verify with `systemctl status douyin-feishu-watcher`
8. Check runtime output with `journalctl -u douyin-feishu-watcher -f`

## Troubleshooting

- If parsing suddenly returns no videos, refresh the fixture and update `app/parser.py`
- If Feishu cards fail, the notifier automatically falls back to plain text
- If the service restarts often, inspect `journalctl` and verify `.env` plus creator URLs
