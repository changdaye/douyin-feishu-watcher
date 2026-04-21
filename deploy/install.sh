#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
  APP_DIR="$SCRIPT_DIR"
else
  APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

SERVICE_NAME="${SERVICE_NAME:-douyin-feishu-watcher}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
SYSTEMD_UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
WHEELHOUSE_DIR="${WHEELHOUSE_DIR:-$APP_DIR/wheelhouse}"

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

if command -v apt-get >/dev/null 2>&1; then
  INSTALL_CMD="$SUDO apt-get update && $SUDO apt-get install -y python3 python3-venv python3-pip ca-certificates sqlite3"
elif command -v dnf >/dev/null 2>&1; then
  INSTALL_CMD="$SUDO dnf install -y python3 python3-pip ca-certificates sqlite"
else
  echo "[ERROR] Supported package manager not found (apt-get or dnf)." >&2
  exit 1
fi

echo "[1/5] Installing base OS dependencies..."
bash -lc "$INSTALL_CMD"

echo "[2/5] Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ -d "$WHEELHOUSE_DIR" ]] && find "$WHEELHOUSE_DIR" -name '*.whl' | grep -q .; then
  echo "[3/5] Installing from bundled wheelhouse..."
  pip install --no-index --find-links "$WHEELHOUSE_DIR" douyin-feishu-watcher
else
  echo "[3/5] Installing from source checkout..."
  pip install -e "$APP_DIR"
fi

echo "[4/5] Preparing runtime directories and permissions..."
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"
chmod 600 "$APP_DIR/local.runtime.json" "$APP_DIR/creators.json"

echo "[5/5] Writing and starting systemd service..."
$SUDO tee "$SYSTEMD_UNIT_PATH" >/dev/null <<UNIT
[Unit]
Description=Douyin Feishu Watcher
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/douyin-feishu-watcher serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

$SUDO systemctl daemon-reload
$SUDO systemctl enable --now "$SERVICE_NAME"

echo
$SUDO systemctl --no-pager --full status "$SERVICE_NAME" || true

echo
printf 'Deployment completed. Useful commands:\n'
printf '  journalctl -u %s -f\n' "$SERVICE_NAME"
printf '  systemctl status %s\n' "$SERVICE_NAME"
printf '  %s run-once\n' "$VENV_DIR/bin/douyin-feishu-watcher"
