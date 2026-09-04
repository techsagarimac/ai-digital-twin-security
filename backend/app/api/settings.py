from fastapi import APIRouter, Depends

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.schemas import SettingsOut, SettingsUpdate
from app.services.camera_service import runtime
from app.services.retention import purge_expired

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _out() -> SettingsOut:
    s = get_settings()
    return SettingsOut(
        detection_confidence=s.detection_confidence,
        object_confidence=s.object_confidence,
        tracking_timeout=s.tracking_timeout,
        process_every_n_frames=s.process_every_n_frames,
        reconstruction_enabled=s.reconstruction_enabled,
        audio_enabled=runtime.audio.enabled,
        demo_mode=runtime.demo_mode or s.demo_mode,
        data_retention_days=s.data_retention_days,
        model_device=s.model_device,
        identity_module_enabled=s.identity_module_enabled,
        microphone="ON" if runtime.audio.enabled else "OFF",
    )


@router.get("", response_model=SettingsOut, summary="Current runtime settings")
def read_settings(_: Principal = Depends(get_principal)) -> SettingsOut:
    return _out()


@router.put("", response_model=SettingsOut, summary="Update runtime settings")
def update_settings(body: SettingsUpdate, _: Principal = Depends(get_principal)) -> SettingsOut:
    s = get_settings()
    data = body.model_dump(exclude_none=True)
    for key, value in data.items():
        if key == "audio_enabled":
            runtime.audio.set_enabled(bool(value), demo=runtime.demo_mode)
            s.audio_enabled = bool(value)
            continue
        setattr(s, key, value)
    if runtime.pipeline:
        runtime.pipeline.settings = s
        runtime.pipeline.tracker.timeout_seconds = s.tracking_timeout
    return _out()


@router.post("/retention/purge", summary="Run data-retention cleanup now")
def run_purge(_: Principal = Depends(get_principal)) -> dict:
    return purge_expired()
