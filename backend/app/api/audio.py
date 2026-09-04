from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.database.database import get_db
from app.events.types import EventType
from app.database import repositories as repo
from app.services.camera_service import runtime
from app.utils.time import utcnow

router = APIRouter(prefix="/api/audio", tags=["audio"])


class AudioToggle(BaseModel):
    enabled: bool


@router.get("", summary="Microphone status")
def audio_status(_: Principal = Depends(get_principal)) -> dict:
    return {
        "microphone": runtime.audio.status_label,
        "enabled": runtime.audio.enabled,
        "engine": runtime.audio.engine,
        "message": runtime.audio.last_error,
        "note": "Microphone never starts secretly. AUDIO_ENABLED and this toggle must both be on.",
    }


@router.post("/toggle", summary="Enable or disable microphone processing")
def toggle_audio(body: AudioToggle, db: Session = Depends(get_db), _: Principal = Depends(get_principal)) -> dict:
    settings = get_settings()
    if body.enabled and not settings.audio_enabled:
        # Allow the operator to enable for the process; config default remains off.
        settings.audio_enabled = True
    runtime.audio.set_enabled(body.enabled, demo=runtime.demo_mode)
    if body.enabled and runtime.demo_mode:
        repo.add_timeline_event(
            db,
            event_type=EventType.SPEECH_DETECTED,
            timestamp=utcnow(),
            camera_id=settings.camera_id,
            metadata={"label": "Microphone enabled (demo). Speech events are simulated."},
            demo=True,
        )
    return audio_status()
