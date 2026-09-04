from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.database.database import get_db
from app.schemas import TimelineEventOut
from app.services.event_service import list_events

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get(
    "",
    response_model=list[TimelineEventOut],
    summary="Search events",
    description="Filter by person/session ID, zone, object/event type, camera, and date range.",
)
def search(
    q: str | None = Query(default=None, description="Person ID or free text"),
    zone_id: str | None = None,
    event_type: str | None = None,
    object_name: str | None = None,
    camera_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[dict]:
    needle = object_name or q
    rows = list_events(
        db,
        person_id=q if q and q.upper().startswith("P") else None,
        event_type=event_type,
        zone_id=zone_id,
        camera_id=camera_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
    )
    if object_name:
        rows = [r for r in rows if object_name.lower() in str(r.get("metadata")).lower() or r.get("type") == "OBJECT_DETECTED"]
        if needle:
            rows = [r for r in rows if object_name.lower() in str(r).lower()]
    return rows
