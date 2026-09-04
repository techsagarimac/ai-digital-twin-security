"""Labeled Demo Mode scenario. Simulated detections are never presented as live AI."""

from __future__ import annotations

import math
from datetime import datetime

import cv2
import numpy as np

from app.utils.geometry import BBox
from app.vision.types import Detection, FaceResult, Landmark, PoseResult

from app.vision.face_mesh import estimate_head_pose


class DemoScenario:
    """A single walking person who turns, enters zones, and leaves.

    All outputs set `simulated=True`. The renderer paints a silhouette so the
    operator can see that this is a generated scene, not a camera capture.
    """

    cycle_seconds = 58.0

    def __init__(self, width: int = 960, height: int = 540) -> None:
        self.width = width
        self.height = height
        self.t0: datetime | None = None

    def elapsed(self, now: datetime) -> float:
        if self.t0 is None:
            self.t0 = now
        return (now - self.t0).total_seconds() % self.cycle_seconds

    def frame(self, now: datetime) -> np.ndarray:
        t = self.elapsed(now)
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        img[:] = (18, 14, 10)
        # Floor grid
        for x in range(0, self.width, 80):
            cv2.line(img, (x, 0), (x, self.height), (32, 28, 24), 1)
        for y in range(0, self.height, 80):
            cv2.line(img, (0, y), (self.width, y), (32, 28, 24), 1)
        cv2.putText(img, "DEMO MODE — SIMULATED SCENE", (24, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 220, 220), 2)
        cv2.putText(img, "Not a live camera capture", (24, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

        state = self._state(t)
        if state is None:
            return img
        x1, y1, x2, y2, yaw = state
        color = (40, 180, 220)
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        # Silhouette
        overlay = img.copy()
        cv2.ellipse(overlay, (int((x1 + x2) / 2), int(y1 + (y2 - y1) * 0.12)), (int((x2 - x1) * 0.18), int((y2 - y1) * 0.08)), 0, 0, 360, (70, 200, 230), -1)
        cv2.rectangle(overlay, (int(x1 + (x2 - x1) * 0.28), int(y1 + (y2 - y1) * 0.2)), (int(x2 - (x2 - x1) * 0.28), int(y1 + (y2 - y1) * 0.62)), (50, 90, 180), -1)
        cv2.rectangle(overlay, (int(x1 + (x2 - x1) * 0.32), int(y1 + (y2 - y1) * 0.62)), (int(x2 - (x2 - x1) * 0.32), int(y2 - 8)), (30, 30, 30), -1)
        img = cv2.addWeighted(overlay, 0.75, img, 0.25, 0)
        cv2.putText(img, f"SIM yaw {yaw:+.0f}", (int(x1), int(y1) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 255, 255), 1)
        return img

    def _state(self, t: float) -> tuple[float, float, float, float, float] | None:
        # Empty at start/end so enter/exit events fire each cycle.
        if t < 2.0 or t > 54.0:
            return None
        progress = (t - 2.0) / 52.0
        cx = self.width * (0.12 + 0.76 * progress)
        cy = self.height * 0.58
        scale = 0.9
        w, h = 140 * scale, 320 * scale
        yaw = 0.0
        if 18 <= t < 26:
            yaw = -55 + (t - 18) * 2  # left
        elif 26 <= t < 34:
            yaw = 50 + (t - 26) * 4  # right then back-ish
        elif 34 <= t < 42:
            yaw = 140
        elif t >= 42:
            yaw = 20
        return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, yaw

    def detections(self, frame: np.ndarray, now: datetime) -> list[Detection]:
        t = self.elapsed(now)
        state = self._state(t)
        if state is None:
            return []
        x1, y1, x2, y2, _yaw = state
        items = [
            Detection(BBox(x1, y1, x2, y2), 0.94, "person", 0, simulated=True),
        ]
        if t >= 8:
            gx1 = x1 + (x2 - x1) * 0.28
            items.append(Detection(BBox(gx1, y1 + 38, gx1 + 48, y1 + 58), 0.91, "glasses", 0, simulated=True))
        if t >= 12:
            items.append(Detection(BBox(x1 - 18, y1 + 80, x1 + 28, y1 + 180), 0.88, "backpack", 0, simulated=True))
        if 20 <= t < 40:
            items.append(Detection(BBox(x2 - 20, y1 + 140, x2 + 10, y1 + 190), 0.81, "phone", 0, simulated=True))
        return items

    def face(self, frame: np.ndarray, person_bbox: BBox | None, now: datetime) -> FaceResult | None:
        t = self.elapsed(now)
        if t < 3.5 or person_bbox is None:
            return None
        _, _, _, _, yaw = self._state(t) or (0, 0, 0, 0, 0)
        w, h = person_bbox.width, person_bbox.height
        bbox = BBox(person_bbox.x1 + w * 0.28, person_bbox.y1 + h * 0.04, person_bbox.x2 - w * 0.28, person_bbox.y1 + h * 0.28)
        fw, fh = bbox.width, bbox.height
        pts = [
            Landmark(33, bbox.x1 + fw * 0.3, bbox.y1 + fh * 0.38, 0.02, 0.9),
            Landmark(263, bbox.x1 + fw * 0.7, bbox.y1 + fh * 0.38, 0.02, 0.9),
            Landmark(1, bbox.x1 + fw * 0.5 + yaw * 0.15, bbox.y1 + fh * 0.55, 0.05, 0.9),
            Landmark(61, bbox.x1 + fw * 0.35, bbox.y1 + fh * 0.75, 0.01, 0.85),
            Landmark(291, bbox.x1 + fw * 0.65, bbox.y1 + fh * 0.75, 0.01, 0.85),
        ]
        # Extra mesh ring so the 3D view has something to draw.
        mesh = list(pts)
        for i in range(16):
            ang = i / 16 * 2 * math.pi
            mesh.append(Landmark(100 + i, bbox.cx + math.cos(ang) * fw * 0.42, bbox.cy + math.sin(ang) * fh * 0.48, 0.03, 0.7))
        eyaw, pitch, roll = estimate_head_pose(pts)
        return FaceResult(bbox=bbox, landmarks=pts, mesh=mesh, yaw=yaw, pitch=pitch or -4.0, roll=roll or 2.0, confidence=0.9, message="SIMULATED")

    def pose(self, frame: np.ndarray, person_bbox: BBox | None, now: datetime) -> PoseResult | None:
        t = self.elapsed(now)
        if t < 4.0 or person_bbox is None:
            return None
        _, _, _, _, yaw = self._state(t) or (0, 0, 0, 0, 0)
        b = person_bbox
        # 17 COCO-style points in bbox space.
        coords = {
            0: (0.50, 0.10),
            1: (0.44, 0.08),
            2: (0.56, 0.08),
            3: (0.40, 0.10),
            4: (0.60, 0.10),
            5: (0.32, 0.22),
            6: (0.68, 0.22),
            7: (0.24, 0.38),
            8: (0.76, 0.38),
            9: (0.22, 0.52),
            10: (0.78, 0.52),
            11: (0.38, 0.52),
            12: (0.62, 0.52),
            13: (0.38, 0.74),
            14: (0.62, 0.74),
            15: (0.36, 0.95),
            16: (0.64, 0.95),
        }
        lms = [
            Landmark(i, b.x1 + b.width * x, b.y1 + b.height * y, 0.0, 0.88)
            for i, (x, y) in coords.items()
        ]
        if yaw > 90:
            orientation = "back-facing"
        elif yaw > 35:
            orientation = "right-facing"
        elif yaw < -35:
            orientation = "left-facing"
        else:
            orientation = "front-facing"
        return PoseResult(landmarks=lms, orientation=orientation, yaw=yaw, confidence=0.9, message="SIMULATED")
