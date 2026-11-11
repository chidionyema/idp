#!/bin/bash
# estate-memory-local: the memory door's local fallback origin, under launchd.
# Serves the estate memory server's own REST contract over one SQLite file. Loopback only.
set -euo pipefail

HOME_DIR="${HOME}"
ROOT="$HOME_DIR/.estate/memory"
STORE="$ROOT/platform/estate/memory/local_store.py"
DB="${ESTATE_MEMORY_DB:-$ROOT/memory.db}"
PORT="${ESTATE_MEMORY_LOCAL_PORT:-8002}"

mkdir -p "$ROOT/logs"
exec /usr/bin/python3 "$STORE" --host 127.0.0.1 --port "$PORT" --db "$DB"
