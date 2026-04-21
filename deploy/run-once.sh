#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
  APP_DIR="$SCRIPT_DIR"
else
  APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
exec "$APP_DIR/.venv/bin/douyin-feishu-watcher" run-once
