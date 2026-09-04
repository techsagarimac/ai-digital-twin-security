"""CSV/JSON exports. Raw biometric and audio payloads are excluded by default."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy.orm import Session

from app.services.analytics_service import build_analytics
from app.services.event_service import list_events
from app.services.person_service import get_person


def timeline_csv(db: Session, person_id: str | None = None) -> str:
    rows = list_events(db, person_id=person_id, limit=2000)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["timestamp", "person_id", "type", "zone_id", "camera_id", "confidence", "label", "demo"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "timestamp": row["timestamp"],
                "person_id": row.get("person_id") or "",
                "type": row["type"],
                "zone_id": row.get("zone_id") or "",
                "camera_id": row["camera_id"],
                "confidence": row["confidence"],
                "label": (row.get("metadata") or {}).get("label", ""),
                "demo": row.get("demo"),
            }
        )
    return buf.getvalue()


def events_json(db: Session, person_id: str | None = None) -> str:
    rows = list_events(db, person_id=person_id, limit=2000)
    # Strip transcript text from default export.
    cleaned = []
    for row in rows:
        meta = dict(row.get("metadata") or {})
        meta.pop("transcript", None)
        item = {**row, "metadata": meta, "timestamp": str(row["timestamp"])}
        cleaned.append(item)
    return json.dumps(cleaned, indent=2, default=str)


def analytics_csv(db: Session) -> str:
    data = build_analytics(db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    writer.writerow(["people_detected", data["people_detected"]])
    writer.writerow(["active_people", data["active_people"]])
    writer.writerow(["events_today", data["events_today"]])
    writer.writerow(["average_dwell_seconds", data["average_dwell_seconds"]])
    writer.writerow(["speech_event_count", data["speech_event_count"]])
    return buf.getvalue()


def person_report(db: Session, person_id: str) -> dict[str, Any]:
    person = get_person(db, person_id)
    if person is None:
        return {}
    recon = person.get("reconstruction") or {}
    return {
        "person_id": person_id,
        "first_seen": str(person.get("first_seen")),
        "last_seen": str(person.get("last_seen")),
        "duration_label": person.get("duration_label"),
        "status": person.get("status"),
        "attributes": person.get("attributes"),
        "reconstruction_coverage": recon.get("coverage", person.get("reconstruction_coverage")),
        "objects": [
            {"object": o.get("object"), "confidence": o.get("confidence")}
            for o in person.get("objects") or []
        ],
        "disclaimer": "Session report. Does not include raw audio or biometric templates.",
    }
