#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DB_PATH:-./data/sqlite/siapsuhu.db}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./db/migrations}"

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 tidak ditemukan. Instal terlebih dahulu." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"

for migration in "${MIGRATIONS_DIR}"/*.sql; do
  [ -e "$migration" ] || continue
  echo "Menjalankan migrasi ${migration}"
  sqlite3 "$DB_PATH" < "$migration"
done

echo "Migrasi selesai -> ${DB_PATH}"
