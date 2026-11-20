#!/bin/sh
set -e
cd "$(dirname "$0")/.."
SKIP=0
for arg in "$@"; do
  if [ "$arg" = "--skip-preflight" ]; then SKIP=1; fi
done
if [ "${SIMAGENT_SKIP_PREFLIGHT:-0}" = "1" ]; then SKIP=1; fi
if [ "$SKIP" = "0" ]; then
  PYTHONPATH=src python3 scripts/preflight.py
fi
if [ -x .venv/bin/pytest ]; then
  PYTHONPATH=src .venv/bin/pytest tests/ -q
elif command -v pytest >/dev/null 2>&1; then
  PYTHONPATH=src pytest tests/ -q
else
  echo "pytest is not installed. Create a virtualenv first:"
  echo "python3 -m venv .venv"
  echo ".venv/bin/pip install -r requirements-dev.txt"
  exit 1
fi
