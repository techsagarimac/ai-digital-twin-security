from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.database.database import get_db
from app.schemas import AnalyticsOut
from app.services.analytics_service import build_analytics

router = APIRouter(tags=["analytics"])


@router.get(
    "/api/analytics",
    response_model=AnalyticsOut,
    summary="Dashboard analytics",
)
def analytics(db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    return build_analytics(db)
