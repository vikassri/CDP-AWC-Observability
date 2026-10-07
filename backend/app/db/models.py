from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512))
    cluster_id: Mapped[str] = mapped_column(String(64))
    product: Mapped[str] = mapped_column(String(64))
    alert_labels: Mapped[dict] = mapped_column(JSON, default=dict)
    metric_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    log_excerpt: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AlertAssignment(Base):
    __tablename__ = "alert_assignments"

    rule_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    product: Mapped[str] = mapped_column(String(64), default="")
    cluster_id: Mapped[str] = mapped_column(String(64), default="")
    emails: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AlertState(Base):
    __tablename__ = "alert_states"

    rule_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    firing: Mapped[bool] = mapped_column(Boolean, default=False)
    last_evaluated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_notified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Remediation(Base):
    __tablename__ = "remediations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    cluster_id: Mapped[str] = mapped_column(String(64))
    action_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    preview: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    approved_by: Mapped[str] = mapped_column(String(128), default="")
    result_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
