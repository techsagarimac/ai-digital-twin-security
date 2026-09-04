from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.database import models
from app.database import repositories as repo
from app.database.database import get_db
from app.schemas import ZoneIn, ZoneOut
from app.services.camera_service import runtime
from app.utils.geometry import BBox
from app.vision.zones import ZoneDef

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut], summary="List camera zones")
def list_zones(db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> list[models.Zone]:
    settings = get_settings()
    repo.seed_default_zones(db, settings.camera_id)
    db.flush()
    return list(db.scalars(select(models.Zone)).all())


@router.post("", response_model=ZoneOut, summary="Create or replace a zone")
def upsert_zone(body: ZoneIn, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> models.Zone:
    if body.x2 <= body.x1 or body.y2 <= body.y1:
        raise HTTPException(status_code=400, detail="zone rectangle is invalid")
    settings = get_settings()
    row = db.get(models.Zone, body.id)
    if row is None:
        row = models.Zone(id=body.id, camera_id=settings.camera_id, name=body.name, x1=body.x1, y1=body.y1, x2=body.x2, y2=body.y2, color=body.color)
        db.add(row)
    else:
        row.name = body.name
        row.x1, row.y1, row.x2, row.y2 = body.x1, body.y1, body.x2, body.y2
        row.color = body.color
    _reload_zones(db)
    return row


@router.delete("/{zone_id}", summary="Delete a zone")
def delete_zone(zone_id: str, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    row = db.get(models.Zone, zone_id)
    if row is None:
        raise HTTPException(status_code=404, detail="zone not found")
    db.delete(row)
    _reload_zones(db)
    return {"ok": True}


def _reload_zones(db: Session) -> None:
    if runtime.pipeline:
        rows = list(db.scalars(select(models.Zone)))
        runtime.pipeline.set_zones([ZoneDef(z.id, z.name, BBox(z.x1, z.y1, z.x2, z.y2), z.color) for z in rows])
