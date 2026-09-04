from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import Principal, get_principal
from app.config import get_settings
from app.schemas import CameraInfo, CameraStartRequest, CameraStopResponse, ErrorResponse
from app.services.camera_service import runtime
from app.utils.images import ALLOWED_VIDEO, ensure_extension, safe_filename

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get(
    "",
    response_model=list[CameraInfo],
    summary="List cameras",
    description="Prototype exposes a single logical camera with the current runtime status.",
)
def list_cameras(_: Principal = Depends(get_principal)) -> list[CameraInfo]:
    snap = runtime.snapshot_status()
    return [CameraInfo(**{k: snap[k] for k in CameraInfo.model_fields if k in snap})]


@router.get("/status", response_model=CameraInfo, summary="Current camera status")
def camera_status(_: Principal = Depends(get_principal)) -> CameraInfo:
    snap = runtime.snapshot_status()
    return CameraInfo(**{k: snap[k] for k in CameraInfo.model_fields if k in snap})


@router.post(
    "/start",
    response_model=CameraInfo,
    responses={400: {"model": ErrorResponse}},
    summary="Start camera",
    description="Start webcam, uploaded video, demo scenario, or RTSP adapter.",
)
def start_camera(body: CameraStartRequest, _: Principal = Depends(get_principal)) -> CameraInfo:
    try:
        snap = runtime.start(
            body.source,
            camera_index=body.camera_index,
            video_path=body.video_path,
            rtsp_url=body.rtsp_url,
            demo_mode=body.demo_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CameraInfo(**{k: snap[k] for k in CameraInfo.model_fields if k in snap})


@router.post("/stop", response_model=CameraStopResponse, summary="Stop camera")
def stop_camera(_: Principal = Depends(get_principal)) -> CameraStopResponse:
    runtime.stop()
    return CameraStopResponse(status="stopped", message="Camera stopped")


@router.post(
    "/frame",
    summary="Push a browser camera JPEG",
    description="Used when the dashboard captures the webcam in-browser (required on many macOS setups).",
)
async def push_frame(file: UploadFile = File(...), _: Principal = Depends(get_principal)) -> dict:
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="frame too large")
    try:
        runtime.ingest_jpeg(data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post(
    "/upload",
    summary="Upload a video file",
    description="Stores a validated video under data/uploads and returns the path for /start.",
)
async def upload_video(file: UploadFile = File(...), _: Principal = Depends(get_principal)) -> dict:
    settings = get_settings()
    name = safe_filename(file.filename or "clip.mp4")
    try:
        ensure_extension(name, ALLOWED_VIDEO)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dest = settings.upload_dir / name
    size = 0
    limit = settings.max_upload_mb * 1024 * 1024
    with dest.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                handle.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="file exceeds MAX_UPLOAD_MB")
            handle.write(chunk)
    return {"path": str(dest), "filename": name, "bytes": size}
