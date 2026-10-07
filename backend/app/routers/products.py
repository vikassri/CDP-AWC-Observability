from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.fleet_overview import fleet_deployment_overview
from backend.app.services.service_overview import product_overview

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/fleet/overview")
async def get_fleet_overview() -> dict:
    return await fleet_deployment_overview()


@router.get("/{product}/overview")
async def get_product_overview(
    product: str,
    cluster: str = Query(..., min_length=1),
) -> dict:
    return await product_overview(product, cluster)
