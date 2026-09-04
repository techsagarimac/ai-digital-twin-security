"""Bounding-box geometry used by detection, tracking, and zones."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def clip(self, width: float, height: float) -> "BBox":
        return BBox(
            x1=float(max(0.0, min(self.x1, width))),
            y1=float(max(0.0, min(self.y1, height))),
            x2=float(max(0.0, min(self.x2, width))),
            y2=float(max(0.0, min(self.y2, height))),
        )

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2.0

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2.0

    @property
    def centroid(self) -> tuple[float, float]:
        return (self.cx, self.cy)

    def as_list(self) -> list[float]:
        return [round(self.x1, 2), round(self.y1, 2), round(self.x2, 2), round(self.y2, 2)]

    def normalized(self, width: float, height: float) -> "BBox":
        width = max(width, 1.0)
        height = max(height, 1.0)
        return BBox(self.x1 / width, self.y1 / height, self.x2 / width, self.y2 / height)

    def iou(self, other: "BBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = self.area + other.area - inter
        if union <= 0:
            return 0.0
        return inter / union


def point_in_rect(x: float, y: float, rect: BBox) -> bool:
    return rect.x1 <= x <= rect.x2 and rect.y1 <= y <= rect.y2
