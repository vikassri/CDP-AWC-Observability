from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

import time

from pydantic import BaseModel, Field

from backend.app.services.promql_helpers import apply_cluster_label
from backend.app.services.prometheus_client import query_prometheus, query_range_prometheus


class MetricsRangeBody(BaseModel):
    query: str = Field(..., min_length=1)
    hours: int = Field(default=6, ge=1, le=168)
    step: str = "60s"
    cluster: str | None = None

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/catalog")
async def metrics_catalog() -> list[dict[str, str]]:
    from backend.app.services.metrics_catalog import load_chart_catalog

    return load_chart_catalog()


@router.get("/job-status")
async def metrics_job_status(
    cluster: str | None = None,
    product: str | None = None,
    fleet: bool = False,
) -> dict:
    from backend.app.services.job_status import job_status_fleet, job_status_for_cluster

    if fleet:
        return await job_status_fleet()
    if not cluster:
        return await job_status_fleet()
    return await job_status_for_cluster(cluster, product)


@router.get("/exporters/status")
async def metrics_exporters_status() -> list[dict]:
    from backend.app.services.status_exporters import status_exporters_state

    return status_exporters_state()


@router.get("/query")
async def metrics_query(
    query: str = Query(..., min_length=1),
    time: str | None = None,
    cluster: str | None = None,
    product: str | None = None,
) -> dict[str, Any]:
    promql = apply_cluster_label(query, cluster)
    if product and "product=" not in promql:
        promql = promql.replace("{", f'{{product="{product}",', 1) if "{" in promql else promql
    try:
        return await query_prometheus(promql, time=time)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _metrics_range_impl(
    query: str,
    hours: int,
    step: str,
    cluster: str | None,
) -> dict[str, Any]:
    promql = apply_cluster_label(query, cluster)
    end = time.time()
    start = end - hours * 3600
    try:
        return await query_range_prometheus(promql, start, end, step=step)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/range")
async def metrics_range_post(body: MetricsRangeBody) -> dict[str, Any]:
    return await _metrics_range_impl(body.query, body.hours, body.step, body.cluster)


@router.get("/range")
async def metrics_range(
    query: str = Query(..., min_length=1),
    hours: int = Query(default=6, ge=1, le=168),
    step: str = "60s",
    cluster: str | None = None,
) -> dict[str, Any]:
    return await _metrics_range_impl(query, hours, step, cluster)
