from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ClusterOut(BaseModel):
    id: str
    display_name: str
    product: str
    context: str
    collectors: list[str]
    awc_console_url: str | None = None
    kubeconfig_ref: str = ""
    kubeconfig_present: bool = False
    awc_engine_id: str = ""
    services: list[str] = Field(default_factory=list)


class ClusterHealthOut(BaseModel):
    id: str
    healthy: bool
    message: str


class EngineOut(BaseModel):
    id: str
    display_name: str
    product: str
    cluster_id: str
    awc_console_url: str
    collectors: list[str]


class MetricsQueryIn(BaseModel):
    query: str
    time: str | None = None


class LogSearchIn(BaseModel):
    cluster: str | None = None
    product: str | None = None
    namespace: str | None = None
    pod: str | None = None
    q: str = "*"
    size: int = 50


class AlertFromLabelsIn(BaseModel):
    title: str
    cluster_id: str
    product: str
    labels: dict[str, Any] = Field(default_factory=dict)
    promql: str | None = None


class IncidentOut(BaseModel):
    id: uuid.UUID
    title: str
    cluster_id: str
    product: str
    status: str
    alert_labels: dict[str, Any]
    metric_snapshot: dict[str, Any]
    log_excerpt: str


class RemediationPreviewIn(BaseModel):
    cluster_id: str
    action_type: str
    namespace: str
    name: str
    kind: str = "deployment"
    incident_id: uuid.UUID | None = None


class RemediationApproveIn(BaseModel):
    approved_by: str = "operator"


class RemediationOut(BaseModel):
    id: uuid.UUID
    cluster_id: str
    action_type: str
    status: str
    preview: str
    result_message: str
