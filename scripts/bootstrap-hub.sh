#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

"${REPO_ROOT}/scripts/copy-kubeconfigs.sh"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — add KNOX_JWT if using Knox scrape."
fi

mkdir -p secrets deploy/data/prometheus/file_sd
if [[ -n "${KNOX_JWT:-}" ]]; then
  printf '%s' "$KNOX_JWT" > secrets/knox.jwt
  chmod 600 secrets/knox.jwt
  echo "Wrote secrets/knox.jwt from KNOX_JWT env."
fi

docker compose -f deploy/docker-compose.yml up -d
echo "Hub stack starting. API: uvicorn backend.app.main:app --reload --port 8080"
