"""Person queries combining live tracks and database history."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models
from app.database import repositories as repo
from app.services.camera_service import runtime
from app.utils.time import duration_seconds, format_duration


def list_people(db: Session) -> list[dict[str, Any]]:
    live = {p["person_id"]: p for p in runtime.latest_people}
    rows = list(db.scalars(select(models.Person).order_by(models.Person.last_seen.desc())))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        live_p = live.get(row.id)
        item = _from_row(db, row, live_p)
        out.append(item)
        seen.add(row.id)
    for pid, live_p in live.items():
        if pid not in seen:
            out.insert(0, live_p)
    return out


def get_person(db: Session, person_id: str) -> dict[str, Any] | None:
    live_p = next((p for p in runtime.latest_people if p["person_id"] == person_id), None)
    row = db.get(models.Person, person_id)
    if row is None and live_p is None:
        return None
    if row is None:
        return live_p
    detail = _from_row(db, row, live_p)
    recon = None
    if runtime.pipeline:
        recon = runtime.pipeline.recon.payload(person_id, (live_p or {}).get("objects"))
    else:
        last = db.scalar(
            select(models.ReconstructionObservation)
            .where(models.ReconstructionObservation.person_id == person_id)
            .order_by(models.ReconstructionObservation.timestamp.desc())
        )
        if last:
            recon = json.loads(last.payload_json)
    detail["reconstruction"] = recon
    objects = list(db.scalars(
        select(models.ObjectDetection)
        .where(models.ObjectDetection.person_id == person_id)
        .order_by(models.ObjectDetection.timestamp.desc())
        .limit(50)
    ))
    detail["objects"] = [
        {
            "object": o.object_name,
            "confidence": o.confidence,
            "bbox": json.loads(o.bbox),
            "timestamp": o.timestamp,
        }
        for o in objects
    ]
    feats = list(db.scalars(select(models.VisibleFeature).where(models.VisibleFeature.person_id == person_id)))
    detail["features"] = [
        {
            "id": f.id,
            "feature_type": f.feature_type,
            "location": f.location,
            "confidence": f.confidence,
            "frame_timestamp": f.frame_timestamp,
            "suppressed": bool(f.suppressed),
            "note": f.note,
        }
        for f in feats
        if not f.suppressed
    ]
    detail["zone_history"] = _zone_history(db, person_id)
    return detail


def _from_row(db: Session, row: models.Person, live: dict[str, Any] | None) -> dict[str, Any]:
    duration = duration_seconds(row.first_seen, row.last_seen)
    clothing = db.scalar(
        select(models.ClothingObservation)
        .where(models.ClothingObservation.person_id == row.id)
        .order_by(models.ClothingObservation.timestamp.desc())
    )
    recon = db.scalar(
        select(models.ReconstructionObservation)
        .where(models.ReconstructionObservation.person_id == row.id)
        .order_by(models.ReconstructionObservation.timestamp.desc())
    )
    det = db.scalar(
        select(models.Detection)
        .where(models.Detection.person_id == row.id)
        .order_by(models.Detection.timestamp.desc())
    )
    attrs = live.get("attributes") if live else None
    if attrs is None and clothing:
        attrs = {
            "hair_presence": clothing.hair_presence,
            "hair_color": clothing.hair_color,
            "hair_style": clothing.hair_style,
            "hair_length": clothing.hair_length,
            "hair_confidence": clothing.hair_confidence,
            "top_label": clothing.top_label,
            "top_color": clothing.top_color,
            "top_confidence": clothing.top_confidence,
            "bottom_label": clothing.bottom_label,
            "bottom_color": clothing.bottom_color,
            "bottom_confidence": clothing.bottom_confidence,
            "shoes_label": clothing.shoes_label,
            "shoes_color": clothing.shoes_color,
            "shoes_confidence": clothing.shoes_confidence,
            "glasses": "UNKNOWN",
            "glasses_confidence": 0.0,
            "backpack": "UNKNOWN",
            "backpack_confidence": 0.0,
        }
    return {
        "person_id": row.id,
        "camera_id": row.camera_id,
        "first_seen": row.first_seen,
        "last_seen": row.last_seen,
        "duration_seconds": duration,
        "duration_label": format_duration(duration),
        "status": "active" if live else row.status,
        "observation_count": row.observation_count,
        "zone_id": (live or {}).get("zone_id") or (det.zone_id if det else None),
        "attributes": attrs or {},
        "reconstruction_coverage": (live or {}).get("reconstruction_coverage") or (recon.coverage if recon else 0.0),
        "confidence": (live or {}).get("confidence") or (det.confidence if det else 0.0),
        "demo": bool(row.demo) or bool((live or {}).get("demo")),
    }


def _zone_history(db: Session, person_id: str) -> list[dict[str, Any]]:
    events = list(
        db.scalars(
            select(models.TimelineEvent)
            .where(
                models.TimelineEvent.person_id == person_id,
                models.TimelineEvent.event_type.in_(["ZONE_ENTERED", "ZONE_EXITED"]),
            )
            .order_by(models.TimelineEvent.timestamp.asc())
        )
    )
    dwell: dict[str, float] = {}
    open_enter: dict[str, Any] = {}
    for ev in events:
        zid = ev.zone_id or "unknown"
        if ev.event_type == "ZONE_ENTERED":
            open_enter[zid] = ev.timestamp
        elif ev.event_type == "ZONE_EXITED" and zid in open_enter:
            dwell[zid] = dwell.get(zid, 0.0) + duration_seconds(open_enter.pop(zid), ev.timestamp)
    from app.utils.time import utcnow

    for zid, ts in list(open_enter.items()):
        dwell[zid] = dwell.get(zid, 0.0) + duration_seconds(ts, utcnow())
    return [{"zone_id": k, "seconds": v, "duration_label": format_duration(v)} for k, v in dwell.items()]
