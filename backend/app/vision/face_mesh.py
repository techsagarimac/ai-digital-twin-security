"""Face bounding box, landmarks, mesh, and approximate head orientation.

OpenCV 5 removed Haar cascades from the Python bindings. This module therefore
tries, in order: MediaPipe, YuNet (FaceDetectorYN), then a skin-region fallback
so a close-up webcam still produces a face box and estimated landmarks.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

from app.utils.geometry import BBox
from app.vision.types import FaceResult, Landmark

logger = logging.getLogger(__name__)


class BaseFaceProcessor(ABC):
    name = "base"

    @abstractmethod
    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        raise NotImplementedError

    def detect_all(self, frame: np.ndarray) -> list[FaceResult]:
        one = self.process(frame, None)
        return [one] if one else []


def _empty(message: str) -> FaceResult:
    return FaceResult(
        bbox=BBox(0, 0, 0, 0),
        landmarks=[],
        mesh=[],
        yaw=None,
        pitch=None,
        roll=None,
        confidence=0.0,
        available=False,
        message=message,
    )


def estimate_head_pose(landmarks: list[Landmark]) -> tuple[float | None, float | None, float | None]:
    """Approximate yaw/pitch/roll from a few facial points. Not medically accurate."""
    by_id = {lm.id: lm for lm in landmarks}
    # MediaPipe-style: 1 nose, 33/263 eyes, 61/291 mouth corners when present.
    left_eye = by_id.get(33) or by_id.get(36) or by_id.get(0)
    right_eye = by_id.get(263) or by_id.get(45) or by_id.get(1)
    nose = by_id.get(1) or by_id.get(30) or by_id.get(2)
    if left_eye is None or right_eye is None:
        if len(landmarks) >= 3:
            left_eye, right_eye, nose = landmarks[0], landmarks[1], landmarks[2]
        else:
            return None, None, None
    dx = right_eye.x - left_eye.x
    dy = right_eye.y - left_eye.y
    roll = float(np.degrees(np.arctan2(dy, dx + 1e-6)))
    mid_x = (left_eye.x + right_eye.x) / 2.0
    eye_span = abs(dx) + 1e-6
    yaw = None
    pitch = None
    if nose is not None:
        yaw = float(np.clip(((nose.x - mid_x) / eye_span) * 90.0, -90.0, 90.0))
        eye_y = (left_eye.y + right_eye.y) / 2.0
        pitch = float(np.clip(((nose.y - eye_y) / eye_span) * 90.0, -45.0, 45.0))
    return yaw, pitch, roll


def landmarks_from_bbox(bbox: BBox, confidence: float = 0.55) -> list[Landmark]:
    w, h = bbox.width, bbox.height
    return [
        Landmark(33, bbox.x1 + w * 0.30, bbox.y1 + h * 0.38, 0.0, confidence),
        Landmark(263, bbox.x1 + w * 0.70, bbox.y1 + h * 0.38, 0.0, confidence),
        Landmark(1, bbox.x1 + w * 0.50, bbox.y1 + h * 0.55, 0.03, confidence),
        Landmark(61, bbox.x1 + w * 0.35, bbox.y1 + h * 0.75, 0.0, confidence * 0.9),
        Landmark(291, bbox.x1 + w * 0.65, bbox.y1 + h * 0.75, 0.0, confidence * 0.9),
    ]


def result_from_bbox(bbox: BBox, confidence: float, message: str, landmarks: list[Landmark] | None = None) -> FaceResult:
    pts = landmarks or landmarks_from_bbox(bbox, confidence)
    yaw, pitch, roll = estimate_head_pose(pts)
    return FaceResult(
        bbox=bbox,
        landmarks=pts,
        mesh=pts,
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        confidence=confidence,
        message=message,
    )


def person_bbox_from_face(face: BBox, frame_w: float, frame_h: float) -> BBox:
    """Expand a face box into an upper-body person box for tracking close-up webcam shots."""
    fw, fh = face.width, face.height
    pad_x = fw * 0.55
    pad_up = fh * 0.35
    pad_down = fh * 2.4
    return BBox(face.x1 - pad_x, face.y1 - pad_up, face.x2 + pad_x, face.y2 + pad_down).clip(frame_w, frame_h)


def _pick_overlapping(faces: list[FaceResult], person_bbox: BBox | None) -> FaceResult | None:
    if not faces:
        return None
    if person_bbox is None:
        return max(faces, key=lambda f: f.bbox.area)
    scored = [(f.bbox.iou(person_bbox), f) for f in faces]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if scored[0][0] > 0.02:
        return scored[0][1]
    return max(faces, key=lambda f: f.bbox.area)


class HaarFaceProcessor(BaseFaceProcessor):
    name = "haar"

    def __init__(self) -> None:
        import cv2

        self._cv2 = cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)
        if self._cascade.empty():
            raise RuntimeError("haar cascade missing")

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        roi = frame
        ox = oy = 0.0
        if person_bbox is not None:
            x1, y1, x2, y2 = map(int, person_bbox.as_list())
            roi = frame[max(0, y1) : max(0, y2), max(0, x1) : max(0, x2)]
            ox, oy = float(max(0, x1)), float(max(0, y1))
        if roi.size == 0:
            return None
        gray = self._cv2.cvtColor(roi, self._cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        bbox = BBox(ox + x, oy + y, ox + x + w, oy + y + h)
        # Approximate 5-point landmarks from the box (clearly estimated).
        pts = [
            Landmark(0, bbox.x1 + w * 0.3, bbox.y1 + h * 0.38, 0.0, 0.45),  # left eye
            Landmark(1, bbox.x1 + w * 0.7, bbox.y1 + h * 0.38, 0.0, 0.45),  # right eye
            Landmark(2, bbox.x1 + w * 0.5, bbox.y1 + h * 0.55, 0.02, 0.45),  # nose
            Landmark(3, bbox.x1 + w * 0.35, bbox.y1 + h * 0.75, 0.0, 0.4),  # mouth L
            Landmark(4, bbox.x1 + w * 0.65, bbox.y1 + h * 0.75, 0.0, 0.4),  # mouth R
        ]
        yaw, pitch, roll = estimate_head_pose(pts)
        return FaceResult(
            bbox=bbox,
            landmarks=pts,
            mesh=pts,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            confidence=0.55,
            message="Approximate landmarks (Haar). Not a face mesh.",
        )


class MediaPipeFaceProcessor(BaseFaceProcessor):
    name = "mediapipe"

    def __init__(self) -> None:
        import mediapipe as mp

        self._mp = mp
        self._landmarker = None
        # Prefer the classic Face Mesh API; it is widely installed with mediapipe.
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        rgb = frame[:, :, ::-1]
        result = self._mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        h, w = frame.shape[:2]
        face = result.multi_face_landmarks[0]
        points: list[Landmark] = []
        xs: list[float] = []
        ys: list[float] = []
        for idx, lm in enumerate(face.landmark):
            x, y, z = lm.x * w, lm.y * h, lm.z
            points.append(Landmark(idx, x, y, z, 0.85))
            xs.append(x)
            ys.append(y)
        bbox = BBox(min(xs), min(ys), max(xs), max(ys))
        key = [p for p in points if p.id in {1, 33, 61, 199, 263, 291}] or points[:5]
        yaw, pitch, roll = estimate_head_pose(key if len(key) >= 3 else points[:5])
        return FaceResult(
            bbox=bbox,
            landmarks=key,
            mesh=points,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            confidence=0.85,
        )


class YuNetFaceProcessor(BaseFaceProcessor):
    """OpenCV FaceDetectorYN (YuNet). Works on OpenCV 5 where Haar was removed."""

    name = "yunet"

    def __init__(self, model_path: str) -> None:
        import cv2

        self._cv2 = cv2
        self._detector = cv2.FaceDetectorYN_create(model_path, "", (320, 320), 0.55, 0.3, 5000)
        self._last_size = (320, 320)

    def detect_all(self, frame: np.ndarray) -> list[FaceResult]:
        h, w = frame.shape[:2]
        if (w, h) != self._last_size:
            self._detector.setInputSize((w, h))
            self._last_size = (w, h)
        _retval, faces = self._detector.detect(frame)
        if faces is None or len(faces) == 0:
            return []
        out: list[FaceResult] = []
        for row in faces:
            x, y, bw, bh = [float(v) for v in row[:4]]
            score = float(row[-1]) if len(row) > 4 else 0.7
            bbox = BBox(x, y, x + bw, y + bh).clip(w, h)
            landmarks = None
            if len(row) >= 15:
                # YuNet: x,y,w,h, rightEye, leftEye, nose, rightMouth, leftMouth, score
                coords = [
                    (33, float(row[4]), float(row[5])),
                    (263, float(row[6]), float(row[7])),
                    (1, float(row[8]), float(row[9])),
                    (61, float(row[10]), float(row[11])),
                    (291, float(row[12]), float(row[13])),
                ]
                landmarks = [Landmark(i, px, py, 0.02, score) for i, px, py in coords]
            out.append(result_from_bbox(bbox, score, "YuNet face detector", landmarks))
        return out

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        return _pick_overlapping(self.detect_all(frame), person_bbox)


class SkinFaceProcessor(BaseFaceProcessor):
    """CPU fallback: largest face-like skin region. Used when YuNet/Haar are missing."""

    name = "skin"

    def detect_all(self, frame: np.ndarray) -> list[FaceResult]:
        import cv2

        h, w = frame.shape[:2]
        if frame.size == 0:
            return []
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        skin = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, kernel, iterations=2)
        skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, kernel, iterations=1)
        contours, _ = cv2.findContours(skin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = max(900.0, 0.012 * w * h)
        max_area = 0.72 * w * h
        hits: list[FaceResult] = []
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < min_area or area > max_area:
                continue
            x, y, bw, bh = cv2.boundingRect(contour)
            if bh < 1:
                continue
            aspect = bw / bh
            if aspect < 0.55 or aspect > 1.55:
                continue
            # Webcam faces sit in the upper two-thirds more often than the floor.
            if y > h * 0.72:
                continue
            bbox = BBox(float(x), float(y), float(x + bw), float(y + bh)).clip(w, h)
            conf = float(min(0.78, 0.45 + area / (w * h)))
            hits.append(result_from_bbox(bbox, conf, "Skin-region face estimate (CPU fallback)"))
        hits.sort(key=lambda f: f.bbox.area, reverse=True)
        return hits[:3]

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        roi = frame
        ox = oy = 0.0
        if person_bbox is not None:
            x1, y1, x2, y2 = map(int, person_bbox.as_list())
            roi = frame[max(0, y1) : max(0, y2), max(0, x1) : max(0, x2)]
            ox, oy = float(max(0, x1)), float(max(0, y1))
        if roi.size == 0:
            return None
        hits = self.detect_all(roi)
        if not hits:
            return None
        best = hits[0]
        shifted = BBox(best.bbox.x1 + ox, best.bbox.y1 + oy, best.bbox.x2 + ox, best.bbox.y2 + oy)
        pts = [
            Landmark(lm.id, lm.x + ox, lm.y + oy, lm.z, lm.confidence)
            for lm in best.landmarks
        ]
        return result_from_bbox(shifted, best.confidence, best.message, pts)


class MockFaceProcessor(BaseFaceProcessor):
    name = "mock"

    def __init__(self, fn) -> None:  # type: ignore[no-untyped-def]
        self._fn = fn

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        return self._fn(frame, person_bbox)


class CompositeFaceProcessor(BaseFaceProcessor):
    """Try accurate detectors first, then the skin-region fallback."""

    name = "composite"

    def __init__(self, processors: list[BaseFaceProcessor]) -> None:
        self.processors = processors
        self.name = "+".join(p.name for p in processors)

    def detect_all(self, frame: np.ndarray) -> list[FaceResult]:
        for proc in self.processors:
            try:
                hits = proc.detect_all(frame)
            except Exception:
                continue
            if hits:
                return hits
        return []

    def process(self, frame: np.ndarray, person_bbox: BBox | None = None) -> FaceResult | None:
        return _pick_overlapping(self.detect_all(frame), person_bbox)


def _yunet_path() -> str | None:
    from app.config import PROJECT_ROOT

    candidates = [
        PROJECT_ROOT / "models" / "face_detection_yunet_2023mar.onnx",
        PROJECT_ROOT / "models" / "face_detection_yunet.onnx",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def create_face_processor(mock: MockFaceProcessor | None = None) -> tuple[BaseFaceProcessor | None, str]:
    if mock is not None:
        return mock, "mock (simulated)"
    chain: list[BaseFaceProcessor] = []
    names: list[str] = []
    try:
        chain.append(MediaPipeFaceProcessor())
        names.append("mediapipe")
        logger.info("model loaded", extra={"event": "model_loaded", "model": "face_mesh"})
    except Exception as exc:
        logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "face_mesh", "error": str(exc)})
    yunet = _yunet_path()
    if yunet:
        try:
            chain.append(YuNetFaceProcessor(yunet))
            names.append("yunet")
            logger.info("model loaded", extra={"event": "model_loaded", "model": "yunet"})
        except Exception as exc:
            logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "yunet", "error": str(exc)})
    try:
        chain.append(HaarFaceProcessor())
        names.append("haar")
        logger.info("model loaded", extra={"event": "model_loaded", "model": "haar_face"})
    except Exception as exc:
        logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "haar_face", "error": str(exc)})
    chain.append(SkinFaceProcessor())
    names.append("skin")
    if not chain:
        return None, "unavailable"
    if len(chain) == 1:
        return chain[0], names[0]
    return CompositeFaceProcessor(chain), "+".join(names)
