from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.audio import router as audio_router
from app.api.camera import router as camera_router
from app.api.events import router as events_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.models_status import router as models_router
from app.api.people import router as people_router
from app.api.search import router as search_router
from app.api.settings import router as settings_router
from app.api.zones import router as zones_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(camera_router)
api_router.include_router(people_router)
api_router.include_router(events_router)
api_router.include_router(models_router)
api_router.include_router(analytics_router)
api_router.include_router(audio_router)
api_router.include_router(zones_router)
api_router.include_router(settings_router)
api_router.include_router(search_router)
api_router.include_router(export_router)
