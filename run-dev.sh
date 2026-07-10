#!/usr/bin/env bash
# GaragePro — DEV launcher (separate copy, separate DB, port 8001).
# Uses the shared venv from the prod copy via the .venv symlink.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

export APP_ENV=dev
export PORT="${PORT:-8001}"
export LOGIN_THROTTLE=false   # no login lockout while developing

# Create the dev database (with demo data) on first run.
if [ ! -f instance/carservice.db ]; then
  echo "[dev] Inicijalizujem dev bazu sa demo podacima…"
  .venv/bin/python init_db.py --demo
fi

echo "[dev] Pokrećem razvojni server na http://0.0.0.0:${PORT} (debug, auto-reload)…"
exec .venv/bin/python run.py
