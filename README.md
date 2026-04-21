# Douyin Feishu Watcher

Python service for polling a small list of public Douyin creators and sending new video alerts to a Feishu webhook bot.

## What it does

- polls public creator pages on a fixed interval
- uses Douyin login cookie to call the creator post API directly when available
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
  build-release.sh
  install.sh
```

## Local development

1. `python3 -m venv .venv`
2. `. .venv/bin/activate`
3. `pip install -e .[dev]`
4. `cp local.runtime.json.example local.runtime.json`
5. `cp creators.json.example creators.json`
6. Fill in `local.runtime.json` and creator profile URLs
7. `pytest tests -q`
8. `douyin-feishu-watcher run-once`

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

## Release bundle

For low-resource or unstable servers, build a fully offline release bundle instead of installing from Git over SSH.

### Build locally on Linux

```bash
bash deploy/build-release.sh
```

This creates an archive like:

```text
dist/douyin-feishu-watcher-linux-x86_64.tar.gz
```

The archive contains:
- `wheelhouse/` with Python wheels
- `install-service.sh` for one-command installation
- `local.runtime.json.example`
- `creators.json.example`
- the systemd unit template

### Install from the bundle on the server

```bash
tar -xzf douyin-feishu-watcher-linux-x86_64.tar.gz
cd douyin-feishu-watcher-linux-x86_64
cp local.runtime.json.example local.runtime.json
cp creators.json.example creators.json
# fill in local.runtime.json and creators.json
bash install-service.sh
```

### GitHub Actions

The repository includes `.github/workflows/release-bundle.yml`.
It builds on GitHub Actions with Python 3.9 so the resulting Linux bundle matches EL9-style servers more closely.
You can trigger it manually from GitHub Actions or publish a `v*` tag to build and upload the Linux bundle artifact automatically.

## Deployment

### One-click install from a checkout

On a server where you already cloned the repo and prepared `local.runtime.json` plus `creators.json`, run:

```bash
bash deploy/install.sh
```

The script will:
- install basic OS dependencies
- create `.venv`
- install from a bundled wheelhouse when present, otherwise from the source checkout
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

- If direct HTTP fetches stop working, refresh `douyin_cookie` in `local.runtime.json`
- If parsing suddenly returns no videos, refresh the fixture and update `app/parser.py`
- If Feishu cards fail, the notifier automatically falls back to plain text
- If the service restarts often, inspect `journalctl` and verify `.env` plus creator URLs
