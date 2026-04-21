#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BUILD_DIR="$DIST_DIR/release-root"
ARCH="${ARCH:-$(uname -m)}"
OS_NAME="${OS_NAME:-$(uname -s | tr "[:upper:]" "[:lower:]")}"
ARCHIVE_BASENAME="douyin-feishu-watcher-${OS_NAME}-${ARCH}"
ARCHIVE_DIR="$BUILD_DIR/$ARCHIVE_BASENAME"
WHEELHOUSE_DIR="$ARCHIVE_DIR/wheelhouse"

rm -rf "$BUILD_DIR"
mkdir -p "$WHEELHOUSE_DIR"

"$PYTHON_BIN" -m pip wheel --wheel-dir "$WHEELHOUSE_DIR" "$ROOT_DIR"

cp "$ROOT_DIR/README.md" "$ARCHIVE_DIR/README.md"
cp "$ROOT_DIR/local.runtime.json.example" "$ARCHIVE_DIR/local.runtime.json.example"
cp "$ROOT_DIR/creators.json.example" "$ARCHIVE_DIR/creators.json.example"
mkdir -p "$ARCHIVE_DIR/deploy"
cp "$ROOT_DIR/deploy/douyin-feishu-watcher.service" "$ARCHIVE_DIR/deploy/"
cp "$ROOT_DIR/deploy/install.sh" "$ARCHIVE_DIR/deploy/"
cp "$ROOT_DIR/deploy/run-once.sh" "$ARCHIVE_DIR/deploy/"
cp "$ROOT_DIR/deploy/service-status.sh" "$ARCHIVE_DIR/deploy/"
cp "$ROOT_DIR/deploy/service-logs.sh" "$ARCHIVE_DIR/deploy/"
cat > "$ARCHIVE_DIR/install-service.sh" <<'WRAP'
#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/deploy/install.sh" "$@"
WRAP
chmod +x "$ARCHIVE_DIR/install-service.sh"

cat > "$ARCHIVE_DIR/run-once.sh" <<'WRAP'
#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/deploy/run-once.sh" "$@"
WRAP
chmod +x "$ARCHIVE_DIR/run-once.sh"

cat > "$ARCHIVE_DIR/service-status.sh" <<'WRAP'
#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/deploy/service-status.sh" "$@"
WRAP
chmod +x "$ARCHIVE_DIR/service-status.sh"

cat > "$ARCHIVE_DIR/service-logs.sh" <<'WRAP'
#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/deploy/service-logs.sh" "$@"
WRAP
chmod +x "$ARCHIVE_DIR/service-logs.sh"

cat > "$ARCHIVE_DIR/RELEASE_INFO.txt" <<INFO
Archive: $ARCHIVE_BASENAME.tar.gz
Built-at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Python: $($PYTHON_BIN --version 2>&1)
INFO

mkdir -p "$DIST_DIR"
tar -czf "$DIST_DIR/$ARCHIVE_BASENAME.tar.gz" -C "$BUILD_DIR" "$ARCHIVE_BASENAME"
echo "$DIST_DIR/$ARCHIVE_BASENAME.tar.gz"
