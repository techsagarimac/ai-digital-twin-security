from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.database.database import get_db
from app.schemas import TimelineEventOut
from app.services.event_service import list_events

router = APIRouter(tags=["events"])


@router.get(
    "/api/events",
    response_model=list[TimelineEventOut],
    summary="List timeline events",
)
def events(
    person_id: str | None = None,
    event_type: str | None = None,
    zone_id: str | None = None,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[dict]:
    return list_events(db, person_id=person_id, event_type=event_type, zone_id=zone_id)


@router.get(
    "/api/events/{person_id}",
    response_model=list[TimelineEventOut],
    summary="Timeline for one person",
)
def person_events(
    person_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> list[dict]:
    return list_events(db, person_id=person_id)
