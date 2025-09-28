#!/usr/bin/env bash
set -euo pipefail

# Launch Node-RED dashboard using the local CLI.
if ! command -v node-red >/dev/null 2>&1; then
  echo "Error: node-red CLI not found. Install it with 'npm install -g node-red'." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$ROOT_DIR/collector/node-red-data"
SQLITE_DIR="$ROOT_DIR/data/sqlite"

export DB_PATH=${DB_PATH:-"$SQLITE_DIR/siapsuhu.db"}

exec node-red -u "$DATA_DIR" "$@"
