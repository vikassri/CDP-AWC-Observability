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

## LLM (OmniRoute)

Set in `.env` or **Settings → AI inference**:

```bash
CPW_LLM_BASE_URL=https://your-omniroute-host/v1
CPW_LLM_MODEL=openai/gpt-4o-mini   # or the model name OmniRoute expects
CPW_LLM_API_KEY=your-omniroute-key
```

The UI calls `POST /recommendations` on the backend only; the backend calls OmniRoute. No API key is sent to the browser.

### TLS / custom CA (OmniRoute HTTPS)

If OmniRoute uses HTTPS signed by a **private or corporate CA**, point Python/httpx at your trust bundle before starting the API:

```bash
export SSL_CERT_FILE=/path/to/your-ca-bundle.pem
# optional: append OmniRoute server cert if needed
# cat omniroute-server.crt >> "$SSL_CERT_FILE"

export PYTHONPATH=.
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8080
```

On macOS you can export a CA from Keychain Access (`.pem`) or combine roots from your security team.

**Mutual TLS (client cert to OmniRoute):** not built into CAO today; terminate mTLS at a sidecar/reverse proxy in front of OmniRoute, or use an API key only on `https://` OmniRoute as usual.

### TLS for the CAO UI (browser)

Recommended: terminate TLS on a reverse proxy, not inside uvicorn.

**Caddy (automatic Let’s Encrypt or your cert files):**

```caddy
cao.example.com {
  tls /etc/ssl/cao/fullchain.pem /etc/ssl/cao/privkey.pem
  reverse_proxy 127.0.0.1:5173
  handle /api/* {
    uri strip_prefix /api
    reverse_proxy 127.0.0.1:8080
  }
}
```

**Direct uvicorn TLS (dev/lab only):**

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile=/path/to/key.pem --ssl-certfile=/path/to/cert.pem
```

Then set the Vite dev proxy target to `https://127.0.0.1:8443` or serve the built `web/dist` from the same proxy.

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
