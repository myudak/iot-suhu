#!/usr/bin/env bash
set -euo pipefail

# Run the Telegram notifier application.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/telegram-notifier"

exec python -m app.main "$@"
