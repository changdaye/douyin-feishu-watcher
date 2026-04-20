# Douyin Feishu Watcher

Python service for polling a small list of public Douyin creators and sending new video alerts to a Feishu webhook bot.

## What it does

- polls public creator pages on a fixed interval
- falls back to headless Playwright when direct HTTP fetches are blocked by Douyin
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
4. `python -m playwright install chromium`
5. `cp .env.example .env`
6. `cp creators.json.example creators.json`
7. Fill in `FEISHU_WEBHOOK_URL` and creator profile URLs
8. `pytest tests -q`
9. `python main.py run-once`

## Environment variables

- `FEISHU_WEBHOOK_URL`: Feishu bot webhook URL
- `FEISHU_BOT_SECRET`: optional Feishu bot signing secret when the bot enables security key checking
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
3. Run `python -m playwright install --with-deps chromium`
4. Create `.env` and `creators.json`
5. Copy `deploy/douyin-feishu-watcher.service` to `/etc/systemd/system/`
5. Run `sudo systemctl daemon-reload`
6. Run `sudo systemctl enable --now douyin-feishu-watcher`
7. Verify with `systemctl status douyin-feishu-watcher`
8. Check runtime output with `journalctl -u douyin-feishu-watcher -f`

## Operational notes

- The very first successful poll builds a baseline and does not send historical videos
- After the baseline exists, only newly discovered video ids are pushed to Feishu
- Repeated failures for the same creator trigger a Feishu text alert once the threshold is reached

## Troubleshooting

- If direct HTTP fetches stop returning HTML, verify Playwright is installed and Chromium can launch
- If parsing suddenly returns no videos, refresh the fixture and update `app/parser.py`
- If Feishu cards fail, the notifier automatically falls back to plain text
- If the service restarts often, inspect `journalctl` and verify `.env` plus creator URLs
