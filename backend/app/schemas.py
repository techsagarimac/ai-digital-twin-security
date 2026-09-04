"""Pydantic contracts for REST and WebSocket payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(APIModel):
    status: str
    app: str
    env: str
    device: str
    demo_mode: bool
    camera: str
    models: dict[str, Any]
    microphone: Literal["ON", "OFF"]
    identity_module: Literal["OFF", "ON"]
    time: datetime


class ErrorResponse(APIModel):
    detail: str


class CameraInfo(APIModel):
    id: str
    source: str
    status: Literal["stopped", "starting", "running", "error"]
    demo_mode: bool
    message: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    device: str = "cpu"


class CameraStartRequest(APIModel):
    source: Literal["webcam", "video", "demo", "rtsp", "browser"] = "webcam"
    camera_index: int | None = None
    video_path: str | None = None
    rtsp_url: str | None = None
    demo_mode: bool | None = None


class CameraStopResponse(APIModel):
    status: str
    message: str


class ZoneIn(APIModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)
    color: str = "#3ee0c5"


class ZoneOut(ZoneIn):
    camera_id: str


class BBoxModel(APIModel):
    x1: float
    y1: float
    x2: float
    y2: float


class LandmarkPoint(APIModel):
    id: int
    x: float
    y: float
    z: float = 0.0
    confidence: float = 0.0


class ObjectOut(APIModel):
    object: str
    confidence: float
    bbox: list[float]
    timestamp: datetime


class AttributeOut(APIModel):
    hair_presence: str = "UNKNOWN"
    hair_color: str = "UNKNOWN"
    hair_style: str = "UNKNOWN"
    hair_length: str = "UNKNOWN"
    hair_confidence: float = 0.0
    top_label: str = "UNKNOWN"
    top_color: str = "UNKNOWN"
    top_confidence: float = 0.0
    bottom_label: str = "UNKNOWN"
    bottom_color: str = "UNKNOWN"
    bottom_confidence: float = 0.0
    shoes_label: str = "UNKNOWN"
    shoes_color: str = "UNKNOWN"
    shoes_confidence: float = 0.0
    glasses: str = "UNKNOWN"
    glasses_confidence: float = 0.0
    backpack: str = "UNKNOWN"
    backpack_confidence: float = 0.0


class VisibleFeatureOut(APIModel):
    id: str
    feature_type: str
    location: str
    confidence: float
    frame_timestamp: datetime
    suppressed: bool = False
    note: str = ""


class ReconstructionOut(APIModel):
    person_id: str
    label: str = "Estimated 3D Model"
    disclaimer: str = (
        "AI-generated geometry from visible landmarks. Not a medical, physical, or X-ray scan."
    )
    coverage: float
    views: dict[str, bool]
    mesh_confidence: float
    insufficient: list[str] = Field(default_factory=list)
    pose_landmarks: list[LandmarkPoint] = Field(default_factory=list)
    face_landmarks: list[LandmarkPoint] = Field(default_factory=list)
    skeleton_edges: list[list[int]] = Field(default_factory=list)
    objects: list[ObjectOut] = Field(default_factory=list)
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None


class PersonLive(APIModel):
    person_id: str
    confidence: float
    bbox: list[float]
    timestamp: datetime
    camera_id: str
    zone_id: str | None = None
    zone_name: str | None = None
    velocity: list[float] = Field(default_factory=lambda: [0.0, 0.0])
    first_seen: datetime
    last_seen: datetime
    duration_seconds: float
    duration_label: str
    observation_count: int
    orientation: str = "UNKNOWN"
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None
    face_bbox: list[float] | None = None
    face_landmarks: list[LandmarkPoint] = Field(default_factory=list)
    pose_landmarks: list[LandmarkPoint] = Field(default_factory=list)
    objects: list[ObjectOut] = Field(default_factory=list)
    attributes: AttributeOut = Field(default_factory=AttributeOut)
    reconstruction_coverage: float = 0.0
    demo: bool = False
    simulated: bool = False


class PersonSummary(APIModel):
    person_id: str
    camera_id: str
    first_seen: datetime
    last_seen: datetime
    duration_seconds: float
    duration_label: str
    status: str
    observation_count: int
    zone_id: str | None = None
    attributes: AttributeOut = Field(default_factory=AttributeOut)
    reconstruction_coverage: float = 0.0
    confidence: float = 0.0
    demo: bool = False


class PersonDetail(PersonSummary):
    reconstruction: ReconstructionOut | None = None
    objects: list[ObjectOut] = Field(default_factory=list)
    features: list[VisibleFeatureOut] = Field(default_factory=list)
    zone_history: list[dict[str, Any]] = Field(default_factory=list)


class TimelineEventOut(APIModel):
    id: str
    person_id: str | None
    type: str
    timestamp: datetime
    camera_id: str
    zone_id: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    demo: bool = False


class AnalyticsOut(APIModel):
    people_per_hour: list[dict[str, Any]]
    average_dwell_seconds: float
    zone_occupancy: list[dict[str, Any]]
    most_visited_zones: list[dict[str, Any]]
    detection_events: list[dict[str, Any]]
    object_detections: list[dict[str, Any]]
    camera_activity: list[dict[str, Any]]
    reconstruction_coverage: list[dict[str, Any]]
    speech_event_count: int
    people_detected: int
    active_people: int
    events_today: int


class SettingsOut(APIModel):
    detection_confidence: float
    object_confidence: float
    tracking_timeout: float
    process_every_n_frames: int
    reconstruction_enabled: bool
    audio_enabled: bool
    demo_mode: bool
    data_retention_days: int
    model_device: str
    identity_module_enabled: bool
    microphone: Literal["ON", "OFF"]


class SettingsUpdate(APIModel):
    detection_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    object_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tracking_timeout: float | None = Field(default=None, ge=0.5, le=60.0)
    process_every_n_frames: int | None = Field(default=None, ge=1, le=15)
    reconstruction_enabled: bool | None = None
    audio_enabled: bool | None = None
    demo_mode: bool | None = None
    data_retention_days: int | None = Field(default=None, ge=1, le=365)


class SearchQuery(APIModel):
    q: str | None = None
    zone_id: str | None = None
    event_type: str | None = None
    object_name: str | None = None
    camera_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class FeaturePatch(APIModel):
    suppressed: bool | None = None
    feature_type: str | None = None
    location: str | None = None
    note: str | None = None


class ModelStatusOut(APIModel):
    detector: str
    face: str
    pose: str
    accessories: str
    speech: str
    device: str
    messages: list[str] = Field(default_factory=list)
