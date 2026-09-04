"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_name: str = "AI 3D Digital Twin Security Camera"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    )

    database_url: str = "sqlite:///./data/twin_security.db"

    camera_id: str = "cam-1"
    camera_source: str = "0"
    target_fps: int = 25
    process_every_n_frames: int = 2
    max_inference_width: int = 640
    jpeg_quality: int = 75
    max_upload_mb: int = 200

    detection_confidence: float = 0.5
    object_confidence: float = 0.5
    tracking_timeout: float = 5.0

    reconstruction_enabled: bool = True
    audio_enabled: bool = False
    demo_mode: bool = False
    model_device: str = "auto"
    yolo_weights: str = "yolov8n.pt"

    data_retention_days: int = 7
    identity_module_enabled: bool = False
    identity_consent: bool = False

    auth_enabled: bool = False
    api_key: str = ""

    @field_validator("detection_confidence", "object_confidence")
    @classmethod
    def _clamp_conf(cls, value: float) -> float:
        return min(1.0, max(0.0, value))

    @field_validator("process_every_n_frames")
    @classmethod
    def _min_stride(cls, value: int) -> int:
        return max(1, value)

    @field_validator("data_retention_days")
    @classmethod
    def _min_retention(cls, value: int) -> int:
        return max(1, value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def data_dir(self) -> Path:
        path = PROJECT_ROOT / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def upload_dir(self) -> Path:
        path = self.data_dir / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def recordings_dir(self) -> Path:
        path = self.data_dir / "recordings"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def audio_dir(self) -> Path:
        path = self.data_dir / "audio"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reconstructions_dir(self) -> Path:
        path = self.data_dir / "reconstructions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def resolved_database_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///./"):
            relative = url.replace("sqlite:///./", "", 1)
            abs_path = (PROJECT_ROOT / relative).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path}"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
