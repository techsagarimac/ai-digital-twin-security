"""Camera-zone occupancy from normalized bounding-box centroids."""

from __future__ import annotations

from dataclasses import dataclass

from app.utils.geometry import BBox, point_in_rect


@dataclass(slots=True)
class ZoneDef:
    id: str
    name: str
    rect: BBox
    color: str = "#3ee0c5"


class ZoneResolver:
    def __init__(self, zones: list[ZoneDef] | None = None) -> None:
        self.zones = zones or []

    def resolve(self, nx: float, ny: float) -> ZoneDef | None:
        for zone in self.zones:
            if point_in_rect(nx, ny, zone.rect):
                return zone
        return None

    def resolve_bbox(self, bbox: BBox, frame_w: float, frame_h: float) -> ZoneDef | None:
        cx, cy = bbox.centroid
        return self.resolve(cx / max(frame_w, 1.0), cy / max(frame_h, 1.0))
