from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.database.database import get_db
from app.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/timeline.csv", summary="Export timeline CSV")
def export_timeline(person_id: str | None = None, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> PlainTextResponse:
    return PlainTextResponse(export_service.timeline_csv(db, person_id), media_type="text/csv")


@router.get("/events.json", summary="Export events JSON (no raw audio)")
def export_events(person_id: str | None = None, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> PlainTextResponse:
    return PlainTextResponse(export_service.events_json(db, person_id), media_type="application/json")


@router.get("/analytics.csv", summary="Export analytics CSV")
def export_analytics(db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> PlainTextResponse:
    return PlainTextResponse(export_service.analytics_csv(db), media_type="text/csv")


@router.get("/people/{person_id}.json", summary="Person session report")
def export_person(person_id: str, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    report = export_service.person_report(db, person_id)
    if not report:
        raise HTTPException(status_code=404, detail="person not found")
    return report
