"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.api.ws import router as ws_router
from app.config import get_settings
from app.database.database import SessionLocal, init_db
from app.database import repositories as repo
from app.logging_config import configure_logging, log_event
from app.services.camera_service import runtime
from app.services.retention import purge_expired

logger = logging.getLogger("twin")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    db = SessionLocal()
    try:
        repo.seed_default_zones(db, settings.camera_id)
        db.commit()
    finally:
        db.close()
    purge_expired()
    runtime.attach_loop(app.state.loop) if hasattr(app.state, "loop") else None
    import asyncio

    runtime.attach_loop(asyncio.get_running_loop())
    log_event(logger, "app_started", camera_id=settings.camera_id)
    yield
    if runtime.status == "running":
        runtime.stop()
    log_event(logger, "app_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Portfolio / engineering prototype: person detection, tracking, visible "
            "attribute analysis, estimated 3D digital twin, and a security dashboard. "
            "RGB cameras do not perform X-ray imaging. The X-ray-style view is a "
            "visualization of AI-derived geometry."
        ),
        version="1.0.0",
        lifespan=lifespan,
        responses={400: {"description": "Validation error"}, 401: {"description": "Unauthorized"}},
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    application.include_router(ws_router)

    @application.exception_handler(HTTPException)
    async def http_exc(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled", extra={"event": "error", "error": str(exc)})
        return JSONResponse(status_code=500, content={"detail": "internal error"})

    return application


app = create_app()
