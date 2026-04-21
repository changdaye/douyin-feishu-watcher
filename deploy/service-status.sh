#!/usr/bin/env bash
set -Eeuo pipefail
SERVICE_NAME="${SERVICE_NAME:-douyin-feishu-watcher}"
exec systemctl status "$SERVICE_NAME" --no-pager --full
