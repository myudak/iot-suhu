#!/usr/bin/env bash
set -euo pipefail

# Launch a local Mosquitto broker without Docker.
if ! command -v mosquitto >/dev/null 2>&1; then
  echo "Error: mosquitto binary not found. Install Mosquitto from https://mosquitto.org/download/." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$ROOT_DIR/data/mosquitto"
mkdir -p "$STATE_DIR"

CONFIG_FILE="$(mktemp)"
cat >"$CONFIG_FILE" <<CONFIG
persistence true
persistence_location $STATE_DIR/

listener 1883
allow_anonymous true

listener 9001
protocol websockets

log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
CONFIG

cleanup() {
  rm -f "$CONFIG_FILE"
}
trap cleanup EXIT

exec mosquitto -c "$CONFIG_FILE" "$@"
