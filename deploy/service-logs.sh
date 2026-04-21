#!/usr/bin/env bash
set -Eeuo pipefail
SERVICE_NAME="${SERVICE_NAME:-douyin-feishu-watcher}"
exec journalctl -u "$SERVICE_NAME" -f
