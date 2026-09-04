"""Person detectors. YOLO preferred, OpenCV HOG fallback, labeled mock for demo."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

from app.utils.geometry import BBox
from app.vision.types import Detection

logger = logging.getLogger(__name__)

PERSON_CLASS = "person"
COCO_PERSON_ID = 0


class BaseDetector(ABC):
    name = "base"

    @abstractmethod
    def detect(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        raise NotImplementedError

    def detect_objects(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        return []


class EmptyDetector(BaseDetector):
    name = "unavailable"

    def detect(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        return []


class HOGDetector(BaseDetector):
    """CPU person detector. No YOLO weights required."""

    name = "hog"

    def __init__(self) -> None:
        import cv2

        self._cv2 = cv2
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        height, width = frame.shape[:2]
        scale = 1.0
        work = frame
        if width > 480:
            scale = 480 / width
            work = self._cv2.resize(frame, (480, max(1, int(height * scale))))
        rects, weights = self._hog.detectMultiScale(
            work,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        out: list[Detection] = []
        for rect, weight in zip(rects, weights):
            score = float(weight[0] if hasattr(weight, "__len__") else weight)
            # HOG scores are not probabilities; squash into 0.4–0.95 for the UI.
            mapped = float(min(0.95, max(0.4, 1 / (1 + np.exp(-score / 2.0)))))
            if mapped < confidence:
                continue
            x, y, w, h = [float(v) / scale for v in rect]
            out.append(
                Detection(
                    bbox=BBox(x, y, x + w, y + h).clip(width, height),
                    confidence=mapped,
                    class_name=PERSON_CLASS,
                    class_id=COCO_PERSON_ID,
                )
            )
        return out


class YOLODetector(BaseDetector):
    name = "yolo"

    def __init__(self, weights: str, device: str) -> None:
        from ultralytics import YOLO

        self._model = YOLO(weights)
        self._device = device if device == "cpu" else device
        self._last_objects: list[Detection] = []

    def detect(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        people, objects = self._infer(frame, confidence)
        self._last_objects = objects
        return people

    def detect_objects(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        if self._last_objects:
            return [item for item in self._last_objects if item.confidence >= confidence]
        _, objects = self._infer(frame, confidence)
        return objects

    def _infer(self, frame: np.ndarray, confidence: float) -> tuple[list[Detection], list[Detection]]:
        height, width = frame.shape[:2]
        results = self._model.predict(
            frame,
            conf=confidence,
            verbose=False,
            device=self._device,
            classes=None,
        )
        people: list[Detection] = []
        objects: list[Detection] = []
        if not results:
            return people, objects
        result = results[0]
        names = result.names or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return people, objects
        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = str(names.get(cls_id, str(cls_id)))
            det = Detection(
                bbox=BBox(xyxy[0], xyxy[1], xyxy[2], xyxy[3]).clip(width, height),
                confidence=conf,
                class_name=label,
                class_id=cls_id,
            )
            if label == PERSON_CLASS:
                people.append(det)
            else:
                objects.append(det)
        return people, objects


class MockDetector(BaseDetector):
    """Scripted detections for Demo Mode. Always labeled simulated."""

    name = "mock"

    def __init__(self, detections_fn) -> None:  # type: ignore[no-untyped-def]
        self._detections_fn = detections_fn

    def detect(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        items = self._detections_fn(frame)
        return [item for item in items if item.class_name == PERSON_CLASS and item.confidence >= confidence]

    def detect_objects(self, frame: np.ndarray, confidence: float) -> list[Detection]:
        items = self._detections_fn(frame)
        return [item for item in items if item.class_name != PERSON_CLASS and item.confidence >= confidence]


def create_detector(prefer_yolo: bool, weights: str, device: str, mock: MockDetector | None = None) -> tuple[BaseDetector, str]:
    if mock is not None:
        return mock, "mock (simulated)"
    if prefer_yolo:
        try:
            detector = YOLODetector(weights, device)
            logger.info("model loaded", extra={"event": "model_loaded", "model": "yolo"})
            return detector, "yolo"
        except Exception as exc:
            logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "yolo", "error": str(exc)})
    try:
        hog = HOGDetector()
        logger.info("model loaded", extra={"event": "model_loaded", "model": "hog"})
        return hog, "hog"
    except Exception as exc:
        logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "hog", "error": str(exc)})
        return EmptyDetector(), "unavailable"
