# Douyin Feishu Watcher

Python service for polling a small list of public Douyin creators and sending new video alerts to a Feishu webhook bot.

## What it does

- polls public creator pages on a fixed interval
- uses Douyin login cookie to call the creator post API directly when available
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
  install.sh
```

## Local development

1. `python3 -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -e .[dev]`
4. `python -m playwright install chromium`
5. `cp local.runtime.json.example local.runtime.json`
6. `cp creators.json.example creators.json`
7. Fill in `local.runtime.json` and creator profile URLs
8. `pytest tests -q`
9. `python main.py run-once`

## Runtime config

The service now prefers a local JSON file such as `local.runtime.json` and falls back to `.env` only for compatibility.

Recommended keys inside `local.runtime.json`:

- `feishu_webhook_url`: Feishu bot webhook URL
- `feishu_bot_secret`: optional Feishu bot signing secret when the bot enables security key checking
- `douyin_cookie`: required for stable access to Douyin creator pages and post APIs
- `creators_file`: creator list JSON path, default `creators.json`
- `sqlite_path`: SQLite database path, default `data/app.db`
- `poll_interval_minutes`: scheduler interval, default `30`
- `request_timeout_seconds`: HTTP timeout, default `15`
- `failure_alert_threshold`: alert threshold, default `3`

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

### One-click server install (recommended)

On an Ubuntu/Debian server, after cloning the repo and preparing `local.runtime.json` plus `creators.json`, run:

```bash
bash deploy/install.sh
```

The script will:
- install OS dependencies
- create `.venv`
- install the Python package
- install Playwright Chromium and required Linux libraries
- write the systemd service
- enable and start the service

### Manual deployment

1. Copy the repo to `/opt/douyin-feishu-watcher`
2. Create `local.runtime.json` and `creators.json`
3. Run `bash deploy/install.sh`
4. Verify with `systemctl status douyin-feishu-watcher`
5. Check runtime output with `journalctl -u douyin-feishu-watcher -f`

## Operational notes

- The very first successful poll builds a baseline and does not send historical videos
- After the baseline exists, only newly discovered video ids are pushed to Feishu
- Repeated failures for the same creator trigger a Feishu text alert once the threshold is reached

## Troubleshooting

- If direct HTTP fetches stop returning HTML, verify Playwright is installed and Chromium can launch
- If parsing suddenly returns no videos, refresh the fixture and update `app/parser.py`
- If Feishu cards fail, the notifier automatically falls back to plain text
- If the service restarts often, inspect `journalctl` and verify `.env` plus creator URLs
