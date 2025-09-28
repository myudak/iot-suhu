#!/usr/bin/env bash
set -euo pipefail

# Start Node-RED dashboard together with Mosquitto via Docker Compose.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

exec docker compose up mosquitto nodered "$@"
