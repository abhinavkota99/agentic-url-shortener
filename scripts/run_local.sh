#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  python3 scripts/bootstrap.py
fi

docker info >/dev/null
python3 scripts/warm_maven_cache.py
docker compose up -d postgres redis backend prometheus grafana

cd orchestrator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Starting orchestrator at http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
