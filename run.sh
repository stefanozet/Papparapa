#!/usr/bin/env bash
# Start Papparapa locally. Creates a virtualenv, installs deps and serves the
# API + frontend on http://localhost:8000
set -e
cd "$(dirname "$0")/backend"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "  ▶  Papparapa è pronto su http://localhost:8000"
echo ""
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
