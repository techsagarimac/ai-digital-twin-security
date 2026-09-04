from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.database.database import get_db
from app.schemas import FeaturePatch, PersonDetail, PersonSummary, ReconstructionOut
from app.services.person_service import get_person, list_people
from app.services.reconstruction_service import get_reconstruction

router = APIRouter(tags=["people"])


@router.get(
    "/api/people",
    response_model=list[PersonSummary],
    summary="List tracked people",
    description="Temporary track IDs (P001…). These are not biometric identities.",
)
def people(db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> list[dict]:
    return list_people(db)


@router.get(
    "/api/people/{person_id}",
    response_model=PersonDetail,
    responses={404: {"description": "Not found"}},
    summary="Person session detail",
)
def person_detail(person_id: str, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    item = get_person(db, person_id)
    if item is None:
        raise HTTPException(status_code=404, detail="person not found")
    return item


@router.get(
    "/api/reconstruction/{person_id}",
    response_model=ReconstructionOut,
    responses={404: {"description": "Not found"}},
    summary="Estimated 3D model",
    description="Fused visible landmarks only. Unseen views are not fabricated.",
)
def reconstruction(person_id: str, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    payload = get_reconstruction(db, person_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="reconstruction not found")
    return payload


@router.patch(
    "/api/people/{person_id}/features/{feature_id}",
    summary="Correct or remove a visible-feature mark",
    description="Operators can suppress or relabel a detected visible feature. Not a medical record.",
)
def patch_feature(
    person_id: str,
    feature_id: str,
    body: FeaturePatch,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_principal),
) -> dict:
    from app.database import models

    row = db.get(models.VisibleFeature, feature_id)
    if row is None or row.person_id != person_id:
        raise HTTPException(status_code=404, detail="feature not found")
    if body.suppressed is not None:
        row.suppressed = 1 if body.suppressed else 0
    if body.feature_type:
        row.feature_type = body.feature_type
    if body.location:
        row.location = body.location
    if body.note is not None:
        row.note = body.note
    return {"ok": True, "id": row.id, "suppressed": bool(row.suppressed)}
