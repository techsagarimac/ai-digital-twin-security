"""Analytics aggregations for the dashboard charts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import models
from app.database.repositories import events_today_count
from app.services.camera_service import runtime
from app.utils.time import utcnow


def build_analytics(db: Session) -> dict[str, Any]:
    now = utcnow()
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hours = [(start_day + timedelta(hours=h)) for h in range(24)]

    people_hour = []
    for h in hours:
        nxt = h + timedelta(hours=1)
        count = db.scalar(
            select(func.count(func.distinct(models.Person.id))).where(
                models.Person.first_seen >= h,
                models.Person.first_seen < nxt,
            )
        )
        people_hour.append({"hour": h.strftime("%H:00"), "count": int(count or 0)})

    sessions = list(db.scalars(select(models.PersonSession)))
    dwells = [s.duration_seconds for s in sessions if s.duration_seconds]
    avg_dwell = sum(dwells) / len(dwells) if dwells else 0.0

    zone_events = list(
        db.scalars(select(models.TimelineEvent).where(models.TimelineEvent.event_type == "ZONE_ENTERED"))
    )
    zone_counts: dict[str, int] = defaultdict(int)
    for ev in zone_events:
        zone_counts[ev.zone_id or "unknown"] += 1
    most_visited = sorted(
        [{"zone": k, "visits": v} for k, v in zone_counts.items()],
        key=lambda x: x["visits"],
        reverse=True,
    )

    occ = []
    for z in db.scalars(select(models.Zone)):
        occ.append({"zone": z.name, "visits": zone_counts.get(z.id, 0)})

    type_counts: dict[str, int] = defaultdict(int)
    for ev in db.scalars(select(models.TimelineEvent)):
        type_counts[ev.event_type] += 1
    detection_events = [{"type": k, "count": v} for k, v in sorted(type_counts.items())]

    obj_counts: dict[str, int] = defaultdict(int)
    for obj in db.scalars(select(models.ObjectDetection)):
        obj_counts[obj.object_name] += 1
    object_detections = [{"object": k, "count": v} for k, v in sorted(obj_counts.items())]

    activity = []
    for h in hours:
        nxt = h + timedelta(hours=1)
        c = db.scalar(
            select(func.count()).select_from(models.Detection).where(models.Detection.timestamp >= h, models.Detection.timestamp < nxt)
        )
        activity.append({"hour": h.strftime("%H:00"), "frames": int(c or 0)})

    recon_rows = list(db.scalars(select(models.ReconstructionObservation)))
    recon = []
    by_person: dict[str, float] = {}
    for row in recon_rows:
        by_person[row.person_id] = max(by_person.get(row.person_id, 0.0), row.coverage)
    for pid, cov in by_person.items():
        recon.append({"person_id": pid, "coverage": cov})

    speech = int(db.scalar(select(func.count()).select_from(models.AudioEvent)) or 0)
    people_detected = int(db.scalar(select(func.count()).select_from(models.Person)) or 0)
    active = len(runtime.latest_people)

    return {
        "people_per_hour": people_hour,
        "average_dwell_seconds": round(avg_dwell, 1),
        "zone_occupancy": occ,
        "most_visited_zones": most_visited,
        "detection_events": detection_events,
        "object_detections": object_detections,
        "camera_activity": activity,
        "reconstruction_coverage": recon,
        "speech_event_count": speech,
        "people_detected": people_detected,
        "active_people": active,
        "events_today": events_today_count(db),
    }
