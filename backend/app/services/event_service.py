"""Timeline / event queries and search filters."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models


def list_events(
    db: Session,
    person_id: str | None = None,
    event_type: str | None = None,
    zone_id: str | None = None,
    camera_id: str | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 400,
) -> list[dict[str, Any]]:
    stmt = select(models.TimelineEvent).order_by(models.TimelineEvent.timestamp.desc()).limit(limit)
    if person_id:
        stmt = stmt.where(models.TimelineEvent.person_id == person_id)
    if event_type:
        stmt = stmt.where(models.TimelineEvent.event_type == event_type)
    if zone_id:
        stmt = stmt.where(models.TimelineEvent.zone_id == zone_id)
    if camera_id:
        stmt = stmt.where(models.TimelineEvent.camera_id == camera_id)
    if date_from:
        stmt = stmt.where(models.TimelineEvent.timestamp >= date_from)
    if date_to:
        stmt = stmt.where(models.TimelineEvent.timestamp <= date_to)
    rows = list(db.scalars(stmt))
    out = [_event_dict(r) for r in rows]
    if q:
        needle = q.lower()
        out = [
            item
            for item in out
            if needle in (item.get("person_id") or "").lower()
            or needle in item["type"].lower()
            or needle in json.dumps(item.get("metadata") or {}).lower()
        ]
    return out


def _event_dict(row: models.TimelineEvent) -> dict[str, Any]:
    try:
        meta = json.loads(row.metadata_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    return {
        "id": row.id,
        "person_id": row.person_id,
        "type": row.event_type,
        "timestamp": row.timestamp,
        "camera_id": row.camera_id,
        "zone_id": row.zone_id,
        "confidence": row.confidence,
        "metadata": meta,
        "demo": bool(row.demo),
    }
