"""End-to-end per-frame vision pipeline with graceful model fallbacks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from app.config import Settings
from app.events.engine import Event, EventEngine, PersonSnapshot
from app.utils.images import encode_jpeg, resize_max_width
from app.utils.time import format_duration, duration_seconds
from app.vision.accessories import associate_objects
from app.vision.attributes import analyze_attributes
from app.vision.demo import DemoScenario
from app.vision.detector import BaseDetector, MockDetector, create_detector
from app.vision.device import resolve_device
from app.vision.face_mesh import BaseFaceProcessor, MockFaceProcessor, create_face_processor, person_bbox_from_face
from app.vision.pose import BasePoseProcessor, MockPoseProcessor, create_pose_processor, estimated_pose_from_face
from app.vision.reconstruction import ReconstructionFuser
from app.vision.tracker import PersonTracker
from app.vision.types import Detection
from app.vision.zones import ZoneDef, ZoneResolver

logger = logging.getLogger(__name__)


@dataclass
class ModelStatus:
    detector: str
    face: str
    pose: str
    accessories: str
    speech: str
    device: str
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "detector": self.detector,
            "face": self.face,
            "pose": self.pose,
            "accessories": self.accessories,
            "speech": self.speech,
            "device": self.device,
            "messages": self.messages,
        }


@dataclass
class PipelineOutput:
    timestamp: datetime
    camera_id: str
    fps: float
    people: list[dict[str, Any]]
    events: list[Event]
    jpeg: bytes
    width: int
    height: int
    demo: bool
    model_status: ModelStatus


class VisionPipeline:
    def __init__(self, settings: Settings, demo_forced: bool = False) -> None:
        self.settings = settings
        self.device = resolve_device(settings.model_device)
        self.demo_forced = demo_forced or settings.demo_mode
        self.demo = DemoScenario() if self.demo_forced else None
        mock_det = MockDetector(self._demo_detections) if self.demo else None
        mock_face = MockFaceProcessor(self._demo_face) if self.demo else None
        mock_pose = MockPoseProcessor(self._demo_pose) if self.demo else None

        self.detector, det_name = create_detector(
            prefer_yolo=not self.demo_forced,
            weights=settings.yolo_weights,
            device=self.device,
            mock=mock_det,
        )
        self.face, face_name = create_face_processor(mock=mock_face)
        self.pose, pose_name = create_pose_processor(mock=mock_pose)
        self.tracker = PersonTracker(timeout_seconds=settings.tracking_timeout)
        self.recon = ReconstructionFuser()
        self.events = EventEngine()
        self.zones = ZoneResolver()
        self._now: datetime | None = None
        self._frame_index = 0
        self._fps = 0.0
        self._last_tick: datetime | None = None
        self._last_objects: list[Detection] = []

        messages: list[str] = []
        if det_name == "unavailable" and face_name not in {"unavailable"}:
            messages.append("Full-body person model unavailable — tracking faces from the webcam instead")
        elif det_name == "unavailable":
            messages.append("Person detection model unavailable")
        if face_name == "unavailable":
            messages.append("Face mesh model unavailable")
        if pose_name == "unavailable":
            messages.append("Pose model unavailable")
        accessories = det_name if det_name in {"yolo", "mock (simulated)"} else "unavailable"
        if accessories == "unavailable":
            messages.append("Accessory detector limited (YOLO not loaded)")
        self.status = ModelStatus(
            detector=det_name,
            face=face_name,
            pose=pose_name,
            accessories=accessories,
            speech="off",
            device=self.device.upper(),
            messages=messages,
        )

    def set_zones(self, zones: list[ZoneDef]) -> None:
        self.zones = ZoneResolver(zones)

    def reset(self) -> None:
        self.tracker.reset()
        self.recon.reset()
        self.events.reset()
        self._frame_index = 0

    def process(self, frame: np.ndarray, timestamp: datetime, camera_id: str) -> PipelineOutput:
        self._now = timestamp
        self._frame_index += 1
        if self._last_tick is not None:
            dt = duration_seconds(self._last_tick, timestamp)
            if dt > 0:
                inst = 1.0 / dt
                self._fps = self._fps * 0.8 + inst * 0.2 if self._fps else inst
        self._last_tick = timestamp

        work, _scale = resize_max_width(frame, self.settings.max_inference_width)
        skip = self._frame_index % self.settings.process_every_n_frames != 0
        if skip and self.tracker.active():
            detections = [
                Detection(t.bbox, t.confidence, "person", 0, simulated=t.simulated) for t in self.tracker.active()
            ]
            objects = self._last_objects
        else:
            detections = self.detector.detect(work, self.settings.detection_confidence)
            try:
                objects = self.detector.detect_objects(work, self.settings.object_confidence)
            except Exception as exc:
                logger.warning("accessory detect failed", extra={"event": "error", "error": str(exc)})
                objects = []
            # Webcam close-ups often have a face but no full-body person box.
            if not detections and self.face is not None:
                try:
                    face_hits = self.face.detect_all(work)
                except Exception:
                    face_hits = []
                fh, fw = work.shape[:2]
                detections = [
                    Detection(
                        bbox=person_bbox_from_face(hit.bbox, fw, fh),
                        confidence=max(hit.confidence, 0.6),
                        class_name="person",
                    )
                    for hit in face_hits
                ]
            self._last_objects = objects

        tracks = self.tracker.update(detections, timestamp)
        closed = self.tracker.pop_closed()
        h, w = work.shape[:2]
        people_payload: list[dict[str, Any]] = []
        snapshots: list[PersonSnapshot] = []

        for track in tracks:
            face = None
            pose = None
            if self.face is not None:
                try:
                    face = self.face.process(work, track.bbox)
                except Exception as exc:
                    logger.warning("face failed", extra={"event": "error", "error": str(exc)})
            if self.pose is not None:
                try:
                    pose = self.pose.process(work, track.bbox)
                except Exception as exc:
                    logger.warning("pose failed", extra={"event": "error", "error": str(exc)})
            if pose is None and face is not None:
                pose = estimated_pose_from_face(face.bbox, w, h)

            attrs = analyze_attributes(
                work,
                track.bbox,
                pose,
                face.bbox if face else None,
                self.settings.detection_confidence,
            )
            hits = associate_objects(objects, track.bbox, self.settings.object_confidence)
            if attrs.glasses == "Detected":
                from app.vision.accessories import AccessoryHit
                from app.utils.geometry import BBox as BB

                if not any(h.name == "glasses" for h in hits) and face is not None:
                    hits.append(AccessoryHit("glasses", attrs.glasses_confidence, face.bbox))

            if any(h.name == "glasses" for h in hits):
                attrs.glasses = "Detected"
                attrs.glasses_confidence = max(h.confidence for h in hits if h.name == "glasses")
            if any(h.name == "backpack" for h in hits):
                attrs.backpack = "Detected"
                attrs.backpack_confidence = max(h.confidence for h in hits if h.name == "backpack")

            recon_state = None
            coverage = 0.0
            if self.settings.reconstruction_enabled:
                recon_state = self.recon.update(track.person_id, timestamp, pose, face)
                coverage = recon_state.coverage

            zone = self.zones.resolve_bbox(track.bbox, w, h)
            duration = duration_seconds(track.first_seen, track.last_seen)
            obj_payload = [
                {
                    "object": hit.name,
                    "confidence": round(hit.confidence, 3),
                    "bbox": hit.bbox.as_list(),
                    "timestamp": timestamp.isoformat(),
                }
                for hit in hits
            ]
            attr_dict = attrs.as_dict()
            attr_dict["backpack"] = attrs.backpack
            attr_dict["backpack_confidence"] = round(attrs.backpack_confidence, 3)

            person = {
                "person_id": track.person_id,
                "confidence": round(track.confidence, 3),
                "bbox": track.bbox.as_list(),
                "timestamp": timestamp.isoformat(),
                "camera_id": camera_id,
                "zone_id": zone.id if zone else None,
                "zone_name": zone.name if zone else None,
                "velocity": [round(track.vx, 3), round(track.vy, 3)],
                "first_seen": track.first_seen.isoformat(),
                "last_seen": track.last_seen.isoformat(),
                "duration_seconds": duration,
                "duration_label": format_duration(duration),
                "observation_count": track.observation_count,
                "orientation": pose.orientation if pose else "UNKNOWN",
                "yaw": face.yaw if face else (pose.yaw if pose else None),
                "pitch": face.pitch if face else None,
                "roll": face.roll if face else None,
                "face_bbox": face.bbox.as_list() if face else None,
                "face_landmarks": [lm.as_dict() for lm in (face.landmarks if face else [])],
                "pose_landmarks": [lm.as_dict() for lm in (pose.landmarks[:17] if pose else [])],
                "objects": obj_payload,
                "attributes": attr_dict,
                "visible_features": attrs.visible_features,
                "reconstruction_coverage": coverage,
                "demo": track.simulated or self.demo_forced,
                "simulated": track.simulated or self.demo_forced,
            }
            people_payload.append(person)
            snapshots.append(
                PersonSnapshot(
                    person_id=track.person_id,
                    zone_id=zone.id if zone else None,
                    has_face=face is not None,
                    objects={h.name for h in hits},
                    orientation=pose.orientation if pose else "UNKNOWN",
                    coverage=coverage,
                    demo=track.simulated or self.demo_forced,
                )
            )

        events = self.events.diff(snapshots, timestamp, camera_id, [t.person_id for t in closed])
        jpeg = encode_jpeg(work, self.settings.jpeg_quality)
        return PipelineOutput(
            timestamp=timestamp,
            camera_id=camera_id,
            fps=round(self._fps, 1),
            people=people_payload,
            events=events,
            jpeg=jpeg,
            width=w,
            height=h,
            demo=self.demo_forced,
            model_status=self.status,
        )

    def _demo_detections(self, frame: np.ndarray) -> list[Detection]:
        assert self.demo and self._now
        return self.demo.detections(frame, self._now)

    def _demo_face(self, frame: np.ndarray, person_bbox):  # type: ignore[no-untyped-def]
        assert self.demo and self._now
        return self.demo.face(frame, person_bbox, self._now)

    def _demo_pose(self, frame: np.ndarray, person_bbox):  # type: ignore[no-untyped-def]
        assert self.demo and self._now
        return self.demo.pose(frame, person_bbox, self._now)
