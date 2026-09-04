from fastapi import APIRouter, Depends

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.schemas import HealthResponse
from app.services.camera_service import runtime
from app.utils.time import utcnow
from app.vision.device import resolve_device

router = APIRouter(tags=["health"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Service health",
    description="Liveness probe plus device, microphone, and model-status snapshot.",
)
def health(_: Principal = Depends(get_principal)) -> HealthResponse:
    settings = get_settings()
    snap = runtime.snapshot_status()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        env=settings.app_env,
        device=resolve_device(settings.model_device).upper(),
        demo_mode=runtime.demo_mode or settings.demo_mode,
        camera=snap["status"],
        models=snap.get("models") or {},
        microphone=snap["microphone"],
        identity_module=snap["identity_module"],
        time=utcnow(),
    )
