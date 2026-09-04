"""Body pose landmarks and coarse facing direction."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

from app.utils.geometry import BBox
from app.vision.types import Landmark, PoseResult

logger = logging.getLogger(__name__)

# Edges for a 17-point COCO-like skeleton used by the 3D viewer.
SKELETON_EDGES = [
    [0, 1],
    [0, 2],
    [1, 3],
    [2, 4],
    [5, 6],
    [5, 7],
    [7, 9],
    [6, 8],
    [8, 10],
    [5, 11],
    [6, 12],
    [11, 12],
    [11, 13],
    [13, 15],
    [12, 14],
    [14, 16],
]


def estimated_pose_from_face(face: BBox, frame_w: float, frame_h: float) -> PoseResult:
    """Low-confidence stick figure derived from a face box when pose models are missing."""
    cx, cy = face.centroid
    fw, fh = max(face.width, 1.0), max(face.height, 1.0)
    coords = {
        0: (cx, cy),
        1: (cx - fw * 0.12, cy - fh * 0.08),
        2: (cx + fw * 0.12, cy - fh * 0.08),
        3: (cx - fw * 0.22, cy),
        4: (cx + fw * 0.22, cy),
        5: (cx - fw * 0.85, cy + fh * 1.1),
        6: (cx + fw * 0.85, cy + fh * 1.1),
        7: (cx - fw * 1.15, cy + fh * 2.0),
        8: (cx + fw * 1.15, cy + fh * 2.0),
        9: (cx - fw * 1.05, cy + fh * 2.7),
        10: (cx + fw * 1.05, cy + fh * 2.7),
        11: (cx - fw * 0.45, cy + fh * 2.6),
        12: (cx + fw * 0.45, cy + fh * 2.6),
        13: (cx - fw * 0.50, cy + fh * 4.0),
        14: (cx + fw * 0.50, cy + fh * 4.0),
        15: (cx - fw * 0.48, cy + fh * 5.2),
        16: (cx + fw * 0.48, cy + fh * 5.2),
    }
    lms = [
        Landmark(i, min(frame_w - 1, max(0.0, x)), min(frame_h - 1, max(0.0, y)), 0.0, 0.35)
        for i, (x, y) in coords.items()
    ]
    return PoseResult(
        landmarks=lms,
        orientation="front-facing",
        yaw=0.0,
        confidence=0.35,
        message="Estimated from face box. Pose model unavailable.",
    )


class BasePoseProcessor(ABC):
    name = "base"

    @abstractmethod
    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> PoseResult | None:
        raise NotImplementedError


def orientation_from_shoulders(left: Landmark, right: Landmark, nose: Landmark | None) -> tuple[str, float | None]:
    dx = right.x - left.x
    if abs(dx) < 1e-3:
        return "UNKNOWN", None
    # If right shoulder appears left of left shoulder, person is likely facing away
    # after a wrap; we use nose relative to shoulder midpoint when available.
    width = abs(dx) + 1e-6
    if nose is None:
        yaw = 0.0
        return "front-facing", yaw
    mid = (left.x + right.x) / 2.0
    offset = (nose.x - mid) / width
    yaw = float(np.clip(offset * 120.0, -180.0, 180.0))
    if dx < 0:
        return "back-facing", 180.0 if yaw >= 0 else -180.0
    if yaw > 35:
        return "right-facing", yaw
    if yaw < -35:
        return "left-facing", yaw
    return "front-facing", yaw


class MediaPipePoseProcessor(BasePoseProcessor):
    name = "mediapipe"

    def __init__(self) -> None:
        import mediapipe as mp

        self._pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> PoseResult | None:
        rgb = frame[:, :, ::-1]
        result = self._pose.process(rgb)
        if not result.pose_landmarks:
            return None
        h, w = frame.shape[:2]
        lms: list[Landmark] = []
        for idx, lm in enumerate(result.pose_landmarks.landmark):
            lms.append(Landmark(idx, lm.x * w, lm.y * h, lm.z, lm.visibility))
        # MediaPipe: 0 nose, 11 left shoulder, 12 right shoulder
        nose = next((p for p in lms if p.id == 0), None)
        left = next((p for p in lms if p.id == 11), None)
        right = next((p for p in lms if p.id == 12), None)
        orientation, yaw = "UNKNOWN", None
        if left and right:
            orientation, yaw = orientation_from_shoulders(left, right, nose)
        conf = float(np.mean([p.confidence for p in lms[:17]])) if lms else 0.0
        return PoseResult(landmarks=lms, orientation=orientation, yaw=yaw, confidence=conf)


class MockPoseProcessor(BasePoseProcessor):
    name = "mock"

    def __init__(self, fn) -> None:  # type: ignore[no-untyped-def]
        self._fn = fn

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> PoseResult | None:
        return self._fn(frame, person_bbox)


def create_pose_processor(mock: MockPoseProcessor | None = None) -> tuple[BasePoseProcessor | None, str]:
    if mock is not None:
        return mock, "mock (simulated)"
    try:
        proc = MediaPipePoseProcessor()
        logger.info("model loaded", extra={"event": "model_loaded", "model": "pose"})
        return proc, "mediapipe"
    except Exception as exc:
        logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "pose", "error": str(exc)})
        return None, "unavailable"
