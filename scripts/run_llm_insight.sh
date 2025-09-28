#!/usr/bin/env bash
set -euo pipefail

# Launch the LLM Insight Service with the FastAPI dev server.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/llm-insight-service"

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

exec python -m uvicorn app.main:app --reload --host "$HOST" --port "$PORT" "$@"
