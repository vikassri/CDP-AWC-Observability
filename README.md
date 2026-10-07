# CDP AWC Observability

Multi-cluster observability for Cloudera Platform on Kubernetes: metrics federation, log forwarding, alerting, incident correlation, and approved Kubernetes remediations.

## Quick start

```bash
./scripts/bootstrap-hub.sh   # kubeconfigs + docker hub stack
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env         # set KNOX_JWT optionally

export PYTHONPATH=.
uvicorn backend.app.main:app --reload --port 8080
```

Web UI:

```bash
cd web && npm install && npm run dev
```

Sign in at http://127.0.0.1:5173 with default credentials **admin** / **admin** (override via `CPW_AUTH_USERNAME`, `CPW_AUTH_PASSWORD`, and `CPW_AUTH_SECRET` in `.env`).

## Configuration

- [`config/clusters.yaml`](config/clusters.yaml) — cluster registry and collectors
- [`config/awc.yaml`](config/awc.yaml) — AWC console deep links
- `kubeconfigs/` — copied from `~/Desktop/uob_poc` (gitignored)
- `secrets/knox.jwt` — optional Knox bearer token for HTTPS scrapes (gitignored)

## Metrics & alert email

1. Start hub stack (Prometheus + Mailpit): `docker compose -f deploy/docker-compose.yml up -d prometheus mailpit`
2. Set SMTP in `.env` (`SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025` for Mailpit). View mail at http://127.0.0.1:8025
3. UI → **Metrics & alerts** — charts per engine; assign comma-separated recipients per rule
4. Optional default recipients: `ALERT_DEFAULT_RECIPIENTS=you@company.com`
5. Test routing: **Test SMTP** in the alert panel, or `POST /alerts/test-email?to=you@company.com`

## API

- `GET /clusters`, `GET /clusters/{id}/health`, `GET /engines`, `GET /awc/catalog`
- `GET /integrations/knox/status` — Knox JWT + scrape target readiness (no secrets returned)
- `GET /metrics/query`, `GET /metrics/range`, `GET /metrics/catalog`
- `GET /alerts/rules`, `PUT /alerts/assignments/{rule_id}`, `POST /alerts/test-email`
- `GET /logs/search`
- `GET /alerts`, `POST /alerts/sync`
- `POST /incidents/from-alert`, `GET /incidents/{id}`
- `POST /remediations/preview`, `POST /remediations/{id}/approve`, `POST /remediations/{id}/execute`
- `GET /collectors/status`

## Docs

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
