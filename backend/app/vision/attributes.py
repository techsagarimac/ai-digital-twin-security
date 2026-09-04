"""Visible clothing and hair from pose/bbox region sampling — not full-frame color."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.utils.confidence import UNKNOWN
from app.utils.geometry import BBox
from app.vision.types import Landmark, PoseResult

HAIR_COLORS = ("Black", "Brown", "Blonde", "Grey", "Other", "Unknown")


@dataclass
class AttributeResult:
    hair_presence: str = UNKNOWN
    hair_color: str = UNKNOWN
    hair_style: str = UNKNOWN
    hair_length: str = UNKNOWN
    hair_confidence: float = 0.0
    top_label: str = UNKNOWN
    top_color: str = UNKNOWN
    top_confidence: float = 0.0
    bottom_label: str = UNKNOWN
    bottom_color: str = UNKNOWN
    bottom_confidence: float = 0.0
    shoes_label: str = UNKNOWN
    shoes_color: str = UNKNOWN
    shoes_confidence: float = 0.0
    glasses: str = UNKNOWN
    glasses_confidence: float = 0.0
    backpack: str = UNKNOWN
    backpack_confidence: float = 0.0
    visible_features: list[dict] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.visible_features is None:
            self.visible_features = []

    def as_dict(self) -> dict:
        return {
            "hair_presence": self.hair_presence,
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "hair_length": self.hair_length,
            "hair_confidence": round(self.hair_confidence, 3),
            "top_label": self.top_label,
            "top_color": self.top_color,
            "top_confidence": round(self.top_confidence, 3),
            "bottom_label": self.bottom_label,
            "bottom_color": self.bottom_color,
            "bottom_confidence": round(self.bottom_confidence, 3),
            "shoes_label": self.shoes_label,
            "shoes_color": self.shoes_color,
            "shoes_confidence": round(self.shoes_confidence, 3),
            "glasses": self.glasses,
            "glasses_confidence": round(self.glasses_confidence, 3),
            "backpack": self.backpack,
            "backpack_confidence": round(self.backpack_confidence, 3),
        }


def _crop(frame: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
    h, w = frame.shape[:2]
    xa, xb = int(max(0, min(w, x1))), int(max(0, min(w, x2)))
    ya, yb = int(max(0, min(h, y1))), int(max(0, min(h, y2)))
    if xb <= xa or yb <= ya:
        return np.empty((0, 0, 3), dtype=np.uint8)
    return frame[ya:yb, xa:xb]


def _bgr_to_color_name(mean_bgr: np.ndarray) -> tuple[str, float]:
    if mean_bgr.size == 0:
        return UNKNOWN, 0.0
    b, g, r = [float(v) for v in mean_bgr]
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx < 40:
        return "Black", 0.72
    if mn > 180 and (mx - mn) < 25:
        return "White", 0.7
    if (mx - mn) < 22:
        if mx > 140:
            return "Grey", 0.62
        return "Black", 0.6
    if r > g + 25 and r > b + 25:
        return "Red" if r > 90 else "Brown", 0.68
    if g > r + 20 and g > b + 15:
        return "Green", 0.65
    if b > r + 20 and b > g + 10:
        return "Blue", 0.7
    if r > 160 and g > 140 and b < 110:
        return "Blonde", 0.58
    if r > 90 and g > 60 and b < 70 and r > g:
        return "Brown", 0.64
    if abs(r - g) < 20 and r > b + 30:
        return "Yellow", 0.6
    return "Other", 0.45


def _band_color(frame: np.ndarray, bbox: BBox, y0: float, y1: float) -> tuple[str, float]:
    region = _crop(frame, bbox.x1 + bbox.width * 0.25, bbox.y1 + bbox.height * y0, bbox.x2 - bbox.width * 0.25, bbox.y1 + bbox.height * y1)
    if region.size == 0:
        return UNKNOWN, 0.0
    mean = region.reshape(-1, 3).mean(axis=0)
    name, conf = _bgr_to_color_name(mean)
    return name, conf


def _glasses_heuristic(frame: np.ndarray, face_bbox: BBox | None) -> tuple[str, float]:
    if face_bbox is None or face_bbox.area < 400:
        return UNKNOWN, 0.0
    eyes = _crop(
        frame,
        face_bbox.x1 + face_bbox.width * 0.12,
        face_bbox.y1 + face_bbox.height * 0.28,
        face_bbox.x2 - face_bbox.width * 0.12,
        face_bbox.y1 + face_bbox.height * 0.52,
    )
    if eyes.size == 0:
        return UNKNOWN, 0.0
    gray = cv2.cvtColor(eyes, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 140)
    density = float(edges.mean() / 255.0)
    if density > 0.08:
        return "Detected", float(min(0.78, 0.4 + density * 2))
    return UNKNOWN, round(density, 3)


def _hair_region(frame: np.ndarray, bbox: BBox, pose: PoseResult | None) -> np.ndarray:
    top = bbox.y1
    if pose and pose.landmarks:
        nose = next((p for p in pose.landmarks if p.id == 0), None)
        if nose:
            top = min(bbox.y1, nose.y - bbox.height * 0.18)
    return _crop(frame, bbox.x1 + bbox.width * 0.2, top, bbox.x2 - bbox.width * 0.2, bbox.y1 + bbox.height * 0.16)


def analyze_attributes(
    frame: np.ndarray,
    bbox: BBox,
    pose: PoseResult | None,
    face_bbox: BBox | None,
    threshold: float,
) -> AttributeResult:
    result = AttributeResult()
    hair = _hair_region(frame, bbox, pose)
    if hair.size:
        mean = hair.reshape(-1, 3).mean(axis=0)
        color, conf = _bgr_to_color_name(mean)
        if color == "White":
            color, conf = "Grey", max(conf, 0.5)
        if color in {"Blue", "Green", "Red", "Yellow"}:
            color, conf = "Other", conf * 0.7
        if conf >= threshold:
            result.hair_presence = "Visible"
            result.hair_color = color if color != "Unknown" else UNKNOWN
            result.hair_confidence = conf
            length_ratio = hair.shape[0] / max(bbox.height, 1)
            if length_ratio < 0.08:
                result.hair_length = "Short"
                result.hair_style = "Short"
            elif length_ratio < 0.14:
                result.hair_length = "Medium"
                result.hair_style = "Medium"
            else:
                result.hair_length = "Long"
                result.hair_style = "Long"
        else:
            result.hair_color = UNKNOWN
            result.hair_confidence = conf

    top_c, top_p = _band_color(frame, bbox, 0.22, 0.48)
    if top_p >= threshold:
        result.top_color = top_c
        result.top_label = f"{top_c} top" if top_c != UNKNOWN else UNKNOWN
        result.top_confidence = top_p
    else:
        result.top_confidence = top_p

    bot_c, bot_p = _band_color(frame, bbox, 0.52, 0.82)
    if bot_p >= threshold:
        result.bottom_color = bot_c
        result.bottom_label = f"{bot_c} trousers" if bot_c != UNKNOWN else UNKNOWN
        result.bottom_confidence = bot_p
    else:
        result.bottom_confidence = bot_p

    shoe_c, shoe_p = _band_color(frame, bbox, 0.86, 0.99)
    if shoe_p >= threshold:
        result.shoes_color = shoe_c
        result.shoes_label = f"{shoe_c} shoes" if shoe_c != UNKNOWN else UNKNOWN
        result.shoes_confidence = shoe_p
    else:
        result.shoes_confidence = shoe_p

    glasses, gconf = _glasses_heuristic(frame, face_bbox)
    if gconf >= threshold and glasses == "Detected":
        result.glasses = "Detected"
        result.glasses_confidence = gconf
    else:
        result.glasses = UNKNOWN
        result.glasses_confidence = gconf

    # Neutral visible-feature layer: high local contrast patches on the face crop.
    if face_bbox and face_bbox.area > 800:
        crop = _crop(frame, face_bbox.x1, face_bbox.y1, face_bbox.x2, face_bbox.y2)
        if crop.size:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            std = float(blur.std())
            if std > 28:
                result.visible_features.append(
                    {
                        "feature_type": "visible feature",
                        "location": "face",
                        "confidence": round(min(0.65, std / 80.0), 3),
                    }
                )
    return result
