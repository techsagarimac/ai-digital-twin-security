"""Persistence helpers. Keep SQL out of API routers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import models
from app.utils.time import duration_seconds, utcnow


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def upsert_person(
    db: Session,
    person_id: str,
    camera_id: str,
    timestamp: datetime,
    demo: bool = False,
) -> models.Person:
    person = db.get(models.Person, person_id)
    if person is None:
        person = models.Person(
            id=person_id,
            camera_id=camera_id,
            first_seen=timestamp,
            last_seen=timestamp,
            status="active",
            observation_count=1,
            demo=1 if demo else 0,
        )
        db.add(person)
    else:
        person.last_seen = timestamp
        person.status = "active"
        person.observation_count += 1
    return person


def close_person(db: Session, person_id: str, timestamp: datetime) -> None:
    person = db.get(models.Person, person_id)
    if person is None:
        return
    person.status = "left"
    person.last_seen = timestamp


def open_session(db: Session, person_id: str, camera_id: str, started_at: datetime) -> models.PersonSession:
    session = models.PersonSession(
        id=str(uuid.uuid4()),
        person_id=person_id,
        camera_id=camera_id,
        started_at=started_at,
        status="open",
    )
    db.add(session)
    return session


def close_open_session(db: Session, person_id: str, ended_at: datetime) -> models.PersonSession | None:
    row = db.scalar(
        select(models.PersonSession)
        .where(models.PersonSession.person_id == person_id, models.PersonSession.status == "open")
        .order_by(models.PersonSession.started_at.desc())
    )
    if row is None:
        return None
    row.ended_at = ended_at
    row.duration_seconds = duration_seconds(row.started_at, ended_at)
    row.status = "closed"
    return row


def add_detection(
    db: Session,
    *,
    person_id: str,
    camera_id: str,
    timestamp: datetime,
    confidence: float,
    bbox: list[float],
    zone_id: str | None,
    demo: bool,
) -> None:
    db.add(
        models.Detection(
            person_id=person_id,
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=confidence,
            bbox=_json(bbox),
            zone_id=zone_id,
            demo=1 if demo else 0,
        )
    )


def add_timeline_event(
    db: Session,
    *,
    event_type: str,
    timestamp: datetime,
    camera_id: str,
    person_id: str | None = None,
    zone_id: str | None = None,
    confidence: float = 1.0,
    metadata: dict[str, Any] | None = None,
    demo: bool = False,
) -> models.TimelineEvent:
    row = models.TimelineEvent(
        id=str(uuid.uuid4()),
        person_id=person_id,
        event_type=event_type,
        timestamp=timestamp,
        camera_id=camera_id,
        zone_id=zone_id,
        confidence=confidence,
        metadata_json=_json(metadata or {}),
        demo=1 if demo else 0,
    )
    db.add(row)
    return row


def add_object(
    db: Session,
    *,
    person_id: str,
    camera_id: str,
    timestamp: datetime,
    object_name: str,
    confidence: float,
    bbox: list[float],
) -> None:
    db.add(
        models.ObjectDetection(
            person_id=person_id,
            camera_id=camera_id,
            timestamp=timestamp,
            object_name=object_name,
            confidence=confidence,
            bbox=_json(bbox),
        )
    )


def add_clothing(db: Session, person_id: str, timestamp: datetime, payload: dict[str, Any]) -> None:
    db.add(
        models.ClothingObservation(
            person_id=person_id,
            timestamp=timestamp,
            top_label=payload.get("top_label", "UNKNOWN"),
            top_color=payload.get("top_color", "UNKNOWN"),
            top_confidence=float(payload.get("top_confidence", 0.0)),
            bottom_label=payload.get("bottom_label", "UNKNOWN"),
            bottom_color=payload.get("bottom_color", "UNKNOWN"),
            bottom_confidence=float(payload.get("bottom_confidence", 0.0)),
            shoes_label=payload.get("shoes_label", "UNKNOWN"),
            shoes_color=payload.get("shoes_color", "UNKNOWN"),
            shoes_confidence=float(payload.get("shoes_confidence", 0.0)),
            hair_presence=payload.get("hair_presence", "UNKNOWN"),
            hair_color=payload.get("hair_color", "UNKNOWN"),
            hair_style=payload.get("hair_style", "UNKNOWN"),
            hair_length=payload.get("hair_length", "UNKNOWN"),
            hair_confidence=float(payload.get("hair_confidence", 0.0)),
        )
    )


def add_face(db: Session, person_id: str, timestamp: datetime, payload: dict[str, Any]) -> None:
    db.add(
        models.FaceObservation(
            person_id=person_id,
            timestamp=timestamp,
            confidence=float(payload.get("confidence", 0.0)),
            bbox=_json(payload.get("bbox", [])),
            yaw=payload.get("yaw"),
            pitch=payload.get("pitch"),
            roll=payload.get("roll"),
            landmarks_json=_json(payload.get("landmarks", [])),
        )
    )


def add_pose(db: Session, person_id: str, timestamp: datetime, payload: dict[str, Any]) -> None:
    db.add(
        models.PoseObservation(
            person_id=person_id,
            timestamp=timestamp,
            orientation=payload.get("orientation", "UNKNOWN"),
            yaw=payload.get("yaw"),
            landmarks_json=_json(payload.get("landmarks", [])),
            confidence=float(payload.get("confidence", 0.0)),
        )
    )


def add_reconstruction(db: Session, person_id: str, timestamp: datetime, payload: dict[str, Any]) -> None:
    views = payload.get("views", {})
    db.add(
        models.ReconstructionObservation(
            person_id=person_id,
            timestamp=timestamp,
            coverage=float(payload.get("coverage", 0.0)),
            front_view=1 if views.get("front") else 0,
            left_view=1 if views.get("left") else 0,
            right_view=1 if views.get("right") else 0,
            back_view=1 if views.get("back") else 0,
            mesh_confidence=float(payload.get("mesh_confidence", 0.0)),
            payload_json=_json(payload),
        )
    )


def list_zones(db: Session, camera_id: str | None = None) -> list[models.Zone]:
    stmt = select(models.Zone)
    if camera_id:
        stmt = stmt.where(models.Zone.camera_id == camera_id)
    return list(db.scalars(stmt))


def seed_default_zones(db: Session, camera_id: str) -> None:
    if list_zones(db, camera_id):
        return
    defaults = [
        models.Zone(id="zone-a", name="Zone A — Entrance", camera_id=camera_id, x1=0.0, y1=0.0, x2=0.33, y2=1.0, color="#3ee0c5"),
        models.Zone(id="zone-b", name="Zone B — Reception", camera_id=camera_id, x1=0.33, y1=0.0, x2=0.66, y2=1.0, color="#6ea8fe"),
        models.Zone(id="zone-c", name="Zone C — Restricted Area", camera_id=camera_id, x1=0.66, y1=0.0, x2=1.0, y2=1.0, color="#f5a524"),
    ]
    db.add_all(defaults)
    db.flush()


def purge_older_than(db: Session, days: int) -> dict[str, int]:
    cutoff = utcnow() - timedelta(days=days)
    counts: dict[str, int] = {}
    tables = [
        models.Detection,
        models.FaceObservation,
        models.LandmarkObservation,
        models.ObjectDetection,
        models.ClothingObservation,
        models.PoseObservation,
        models.ReconstructionObservation,
        models.TimelineEvent,
        models.AudioEvent,
        models.Transcription,
        models.VisibleFeature,
    ]
    for table in tables:
        ts_col = getattr(table, "timestamp", None) or getattr(table, "frame_timestamp", None)
        if ts_col is None:
            continue
        result = db.execute(delete(table).where(ts_col < cutoff))
        counts[table.__tablename__] = result.rowcount or 0
    return counts


def events_today_count(db: Session) -> int:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return int(db.scalar(select(func.count()).select_from(models.TimelineEvent).where(models.TimelineEvent.timestamp >= start)) or 0)
