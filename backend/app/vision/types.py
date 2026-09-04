"""Shared vision dataclasses. Implementations stay behind interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.utils.geometry import BBox


@dataclass(slots=True)
class Detection:
    bbox: BBox
    confidence: float
    class_name: str
    class_id: int = 0
    simulated: bool = False


@dataclass(slots=True)
class Landmark:
    id: int
    x: float
    y: float
    z: float = 0.0
    confidence: float = 0.0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "x": round(self.x, 4),
            "y": round(self.y, 4),
            "z": round(self.z, 4),
            "confidence": round(self.confidence, 4),
        }


@dataclass(slots=True)
class FaceResult:
    bbox: BBox
    landmarks: list[Landmark]
    mesh: list[Landmark]
    yaw: float | None
    pitch: float | None
    roll: float | None
    confidence: float
    available: bool = True
    message: str = ""


@dataclass(slots=True)
class PoseResult:
    landmarks: list[Landmark]
    orientation: str
    yaw: float | None
    confidence: float
    available: bool = True
    message: str = ""


@dataclass(slots=True)
class Track:
    person_id: str
    bbox: BBox
    confidence: float
    first_seen: datetime
    last_seen: datetime
    observation_count: int = 1
    vx: float = 0.0
    vy: float = 0.0
    hits: int = 1
    misses: int = 0
    simulated: bool = False
    class_name: str = "person"

    @property
    def centroid(self) -> tuple[float, float]:
        return self.bbox.centroid
