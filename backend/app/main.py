from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db.session import Base, engine
from backend.app.middleware.auth_gate import AuthGateMiddleware
from backend.app.routers import (
    alerts,
    app_settings_router,
    auth,
    awc,
    clusters,
    collectors,
    incidents,
    integrations,
    logs,
    metrics,
    nifi,
    products,
    recommendations,
    remediations,
)
from backend.app.routers.clusters import router_engines
from backend.app.db.session import SessionLocal
from backend.app.services.alert_bootstrap import ensure_alert_assignments
from backend.app.services.alert_engine import alert_engine
from backend.app.services.collector_supervisor import supervisor
from backend.app.services.knox_secrets import sync_knox_jwt_file

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_knox_jwt_file()
    from collectors.knox_sd import sync_knox_targets

    sync_knox_targets()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await ensure_alert_assignments(session)
    await supervisor.start()
    await alert_engine.start()
    yield
    await alert_engine.stop()
    await supervisor.stop()


app = FastAPI(title="CDP AWC Observability", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthGateMiddleware)

app.include_router(auth.router)
app.include_router(clusters.router)
app.include_router(router_engines)
app.include_router(awc.router)
app.include_router(integrations.router)
app.include_router(metrics.router)
app.include_router(nifi.router)
app.include_router(products.router)
app.include_router(recommendations.router)
app.include_router(logs.router)
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(remediations.router)
app.include_router(collectors.router)
app.include_router(app_settings_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
