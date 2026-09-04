"""Safe image helpers: resize, JPEG encode, validated uploads."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import cv2
import numpy as np

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
ALLOWED_VIDEO = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png"}


def safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = SAFE_NAME.sub("_", base).strip("._")
    if not cleaned:
        cleaned = f"upload_{uuid.uuid4().hex}"
    return cleaned[:120]


def ensure_extension(name: str, allowed: set[str]) -> str:
    suffix = Path(name).suffix.lower()
    if suffix not in allowed:
        raise ValueError(f"unsupported file type: {suffix or 'none'}")
    return name


def resize_max_width(frame: np.ndarray, max_width: int) -> tuple[np.ndarray, float]:
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame, 1.0
    scale = max_width / float(width)
    resized = cv2.resize(
        frame,
        (max_width, max(1, int(height * scale))),
        interpolation=cv2.INTER_LINEAR,
    )
    return resized, scale


def encode_jpeg(frame: np.ndarray, quality: int = 75) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("jpeg encode failed")
    return buf.tobytes()


def bgr_mean(region: np.ndarray) -> tuple[float, float, float]:
    if region.size == 0:
        return (0.0, 0.0, 0.0)
    means = region.reshape(-1, 3).mean(axis=0)
    return float(means[0]), float(means[1]), float(means[2])
