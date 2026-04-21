#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="${SERVICE_NAME:-douyin-feishu-watcher}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
SYSTEMD_UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -f "$APP_DIR/pyproject.toml" || ! -f "$APP_DIR/main.py" ]]; then
  echo "[ERROR] APP_DIR does not look like the douyin-feishu-watcher repository: $APP_DIR" >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/local.runtime.json" ]]; then
  echo "[ERROR] Missing $APP_DIR/local.runtime.json" >&2
  echo "Copy local.runtime.json.example to local.runtime.json and fill in your secrets first." >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/creators.json" ]]; then
  echo "[ERROR] Missing $APP_DIR/creators.json" >&2
  echo "Copy creators.json.example to creators.json and fill in your subscribed creators first." >&2
  exit 1
fi

if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  SUDO=""
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "[ERROR] This install script currently supports Ubuntu/Debian systems with apt-get." >&2
  exit 1
fi

echo "[1/7] Installing OS dependencies..."
$SUDO apt-get update
$SUDO apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  ca-certificates \
  curl \
  sqlite3

echo "[2/7] Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

echo "[3/7] Installing Python project..."
pip install -e "$APP_DIR"

echo "[4/7] Installing Playwright Chromium and Linux deps..."
python -m playwright install --with-deps chromium

echo "[5/7] Preparing runtime directories and permissions..."
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"
chmod 600 "$APP_DIR/local.runtime.json" "$APP_DIR/creators.json"

echo "[6/7] Writing systemd service..."
$SUDO tee "$SYSTEMD_UNIT_PATH" >/dev/null <<UNIT
[Unit]
Description=Douyin Feishu Watcher
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python $APP_DIR/main.py serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

echo "[7/7] Enabling and starting service..."
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now "$SERVICE_NAME"

echo
$SUDO systemctl --no-pager --full status "$SERVICE_NAME" || true

echo
printf 'Deployment completed. Useful commands:\n'
printf '  journalctl -u %s -f\n' "$SERVICE_NAME"
printf '  systemctl status %s\n' "$SERVICE_NAME"
printf '  %s/main.py run-once\n' "$VENV_DIR/bin/python"
