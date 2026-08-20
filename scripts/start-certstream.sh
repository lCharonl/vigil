#!/usr/bin/env bash
# Starts the local certstream-server-rust instance vigil watch talks to by
# default (ws://127.0.0.1:8080/). See docs/architecture.md.
set -euo pipefail

CERTSTREAM_DIR="${CERTSTREAM_DIR:-$HOME/Projet/certstream-server-rust}"
BIN="$CERTSTREAM_DIR/target/release/certstream-server-rust"
LOG_FILE="$CERTSTREAM_DIR/certstream-server.log"

if pgrep -f "$BIN" >/dev/null 2>&1; then
    echo "certstream-server-rust is already running (pid $(pgrep -f "$BIN" | head -1))"
    exit 0
fi

if [ ! -x "$BIN" ]; then
    echo "binary not found at $BIN — build it first: (cd $CERTSTREAM_DIR && cargo build --release)" >&2
    exit 1
fi

cd "$CERTSTREAM_DIR"
nohup "$BIN" > "$LOG_FILE" 2>&1 &
disown

echo "starting certstream-server-rust (pid $!), logging to $LOG_FILE"

for _ in $(seq 1 10); do
    sleep 1
    if curl -sf --max-time 1 http://localhost:8080/health >/dev/null 2>&1; then
        echo "up: http://localhost:8080/health"
        exit 0
    fi
done

echo "server did not become healthy in time, check $LOG_FILE" >&2
exit 1
