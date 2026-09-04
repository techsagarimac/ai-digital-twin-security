from fastapi import APIRouter, Depends

from app.api.deps import Principal, get_principal
from app.schemas import ModelStatusOut
from app.services.camera_service import runtime

router = APIRouter(tags=["models"])


@router.get(
    "/api/models",
    response_model=ModelStatusOut,
    summary="AI component status",
    description="Reports which detectors are loaded versus unavailable. Missing models do not crash the app.",
)
def models(_: Principal = Depends(get_principal)) -> dict:
    snap = runtime.snapshot_status()
    models = snap.get("models") or {}
    return {
        "detector": models.get("detector", "idle"),
        "face": models.get("face", "idle"),
        "pose": models.get("pose", "idle"),
        "accessories": models.get("accessories", "idle"),
        "speech": models.get("speech", "off"),
        "device": models.get("device", "cpu"),
        "messages": models.get("messages") or [],
    }
