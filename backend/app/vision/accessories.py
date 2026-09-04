"""Visible accessory / object detections associated with a person bbox."""

from __future__ import annotations

from dataclasses import dataclass

from app.utils.geometry import BBox
from app.vision.types import Detection

SECURITY_OBJECTS = {
    "backpack",
    "handbag",
    "umbrella",
    "bottle",
    "cell phone",
    "suitcase",
    "tie",
    "laptop",
    "book",
    "clock",
    "sports ball",
    "hat",
    "helmet",
    "glasses",
    "watch",
    "phone",
}

# Map COCO / detector labels onto the security vocabulary.
ALIASES = {
    "cell phone": "phone",
    "handbag": "handbag",
    "wine glass": "bottle",
    "cup": "bottle",
}


@dataclass(slots=True)
class AccessoryHit:
    name: str
    confidence: float
    bbox: BBox
    timestamp: str | None = None


def associate_objects(
    objects: list[Detection],
    person: BBox,
    threshold: float,
    iou_min: float = 0.02,
) -> list[AccessoryHit]:
    hits: list[AccessoryHit] = []
    for det in objects:
        label = ALIASES.get(det.class_name, det.class_name)
        if label not in SECURITY_OBJECTS and det.class_name not in SECURITY_OBJECTS:
            continue
        if det.confidence < threshold:
            continue
        # Keep objects that overlap the person or sit immediately adjacent (held items).
        expanded = BBox(person.x1 - person.width * 0.15, person.y1 - person.height * 0.1, person.x2 + person.width * 0.15, person.y2 + person.height * 0.1)
        if det.bbox.iou(expanded) < iou_min and not _center_inside(det.bbox, expanded):
            continue
        hits.append(AccessoryHit(name=label, confidence=det.confidence, bbox=det.bbox))
    return hits


def _center_inside(inner: BBox, outer: BBox) -> bool:
    cx, cy = inner.centroid
    return outer.x1 <= cx <= outer.x2 and outer.y1 <= cy <= outer.y2
