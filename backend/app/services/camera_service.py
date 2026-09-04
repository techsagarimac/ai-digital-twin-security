"""Background camera loop: capture → pipeline → persist → websocket."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.audio.transcription import AudioGateway
from app.camera.base import BaseCameraSource, DemoSource, PushFrameSource, RTSPSource, VideoFileSource, WebcamSource
from app.config import Settings, get_settings
from app.database import repositories as repo
from app.database.database import SessionLocal
from app.events.types import EventType
from app.identity.module import IdentityModule
from app.utils.time import utcnow
from app.vision.demo import DemoScenario
from app.vision.pipeline import PipelineOutput, VisionPipeline
from app.vision.zones import ZoneDef
from app.utils.geometry import BBox
from app.ws.manager import manager

logger = logging.getLogger(__name__)


class CameraRuntime:
    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        self.status = "stopped"
        self.message = "Camera idle"
        self.source_name = "none"
        self.demo_mode = False
        self.fps = 0.0
        self.width = 0
        self.height = 0
        self.latest_frame: dict[str, Any] | None = None
        self.latest_people: list[dict[str, Any]] = []
        self.pipeline: VisionPipeline | None = None
        self.audio = AudioGateway()
        self.identity = IdentityModule(self.settings.identity_module_enabled, self.settings.identity_consent)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._source: BaseCameraSource | None = None
        self._session_id: str | None = None
        self._last_persist = 0.0
        self._demo_speech_fired = False

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def snapshot_status(self) -> dict[str, Any]:
        models = self.pipeline.status.as_dict() if self.pipeline else {
            "detector": "idle",
            "face": "idle",
            "pose": "idle",
            "accessories": "idle",
            "speech": self.audio.engine,
            "device": "cpu",
            "messages": [],
        }
        models["speech"] = self.audio.engine if self.audio.enabled else "off"
        return {
            "id": self.settings.camera_id,
            "source": self.source_name,
            "status": self.status,
            "demo_mode": self.demo_mode,
            "message": self.message,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "device": models.get("device", "cpu"),
            "models": models,
            "microphone": self.audio.status_label,
            "identity_module": "ON" if self.identity.enabled else "OFF",
            "clients": manager.count,
        }

    def start(self, source_kind: str, **kwargs: Any) -> dict[str, Any]:
        if self.status == "running":
            self.stop()
        self.settings = get_settings()
        demo = bool(kwargs.get("demo_mode", self.settings.demo_mode) or source_kind == "demo")
        self.demo_mode = demo
        self.pipeline = VisionPipeline(self.settings, demo_forced=demo)
        self._load_zones()
        self._source = self._build_source(source_kind, demo=demo, **kwargs)
        try:
            self._source.open()
        except Exception as exc:
            self.status = "error"
            self.message = str(exc)
            logger.error("camera start failed", extra={"event": "error", "error": str(exc)})
            if source_kind != "demo" and source_kind != "browser":
                # Fall back to demo so the dashboard still works.
                logger.warning("falling back to demo source", extra={"event": "camera_started"})
                demo = True
                self.demo_mode = True
                self.pipeline = VisionPipeline(self.settings, demo_forced=True)
                self._load_zones()
                self._source = DemoSource(self.pipeline.demo or DemoScenario())
                self._source.open()
                self.message = f"Requested source failed ({exc}). Running DEMO MODE."
            else:
                raise
        self.source_name = self._source.name
        self.width, self.height = self._source.size
        self._stop.clear()
        self._demo_speech_fired = False
        self.status = "running"
        if not self.message.startswith("Requested"):
            self.message = "DEMO MODE" if demo else "Camera running"
        self._session_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            from app.database import models

            db.add(
                models.CameraSession(
                    id=self._session_id,
                    camera_id=self.settings.camera_id,
                    source=self.source_name,
                    demo=1 if demo else 0,
                    status="running",
                )
            )
            repo.add_timeline_event(
                db,
                event_type=EventType.CAMERA_STARTED,
                timestamp=utcnow(),
                camera_id=self.settings.camera_id,
                metadata={"label": "Camera started", "source": self.source_name},
                demo=demo,
            )
            db.commit()
        finally:
            db.close()
        self._thread = threading.Thread(target=self._run, name="camera-loop", daemon=True)
        self._thread.start()
        return self.snapshot_status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._source:
            try:
                self._source.close()
            except Exception:
                pass
        self._source = None
        self.status = "stopped"
        self.message = "Camera idle"
        db = SessionLocal()
        try:
            if self._session_id:
                from app.database import models

                row = db.get(models.CameraSession, self._session_id)
                if row:
                    row.ended_at = utcnow()
                    row.status = "stopped"
            repo.add_timeline_event(
                db,
                event_type=EventType.CAMERA_STOPPED,
                timestamp=utcnow(),
                camera_id=self.settings.camera_id,
                metadata={"label": "Camera stopped"},
                demo=self.demo_mode,
            )
            db.commit()
        finally:
            db.close()
        logger.info("camera stopped", extra={"event": "camera_stopped", "camera_id": self.settings.camera_id})
        return self.snapshot_status()

    def ingest_jpeg(self, data: bytes) -> None:
        """Accept a browser-captured JPEG and feed it into the live pipeline."""
        import cv2
        import numpy as np

        if self.status != "running":
            raise RuntimeError("start the camera first")
        arr = np.frombuffer(data, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("invalid jpeg")
        if isinstance(self._source, PushFrameSource):
            self._source.push(frame)
            return
        # Swap an OpenCV webcam for the browser feed so macOS camera permission works.
        previous = self._source
        push = PushFrameSource()
        push.open()
        push.push(frame)
        self._source = push
        self.source_name = push.name
        if previous is not None:
            try:
                previous.close()
            except Exception:
                pass

    def _build_source(self, kind: str, demo: bool, **kwargs: Any) -> BaseCameraSource:
        if kind == "demo" or (demo and kind not in {"webcam", "video", "rtsp", "browser"}):
            scenario = self.pipeline.demo if self.pipeline and self.pipeline.demo else DemoScenario()
            return DemoSource(scenario)
        if kind == "browser":
            return PushFrameSource()
        if kind == "webcam":
            index = int(kwargs.get("camera_index") if kwargs.get("camera_index") is not None else self.settings.camera_source or 0)
            return WebcamSource(index)
        if kind == "video":
            path = kwargs.get("video_path")
            if not path:
                raise ValueError("video_path is required")
            return VideoFileSource(str(path), loop=True)
        if kind == "rtsp":
            url = kwargs.get("rtsp_url")
            if not url:
                raise ValueError("rtsp_url is required")
            return RTSPSource(str(url))
        raise ValueError(f"unknown camera source: {kind}")

    def _load_zones(self) -> None:
        if not self.pipeline:
            return
        db = SessionLocal()
        try:
            repo.seed_default_zones(db, self.settings.camera_id)
            db.commit()
            rows = repo.list_zones(db, self.settings.camera_id)
            self.pipeline.set_zones(
                [ZoneDef(z.id, z.name, BBox(z.x1, z.y1, z.x2, z.y2), z.color) for z in rows]
            )
        finally:
            db.close()

    def _run(self) -> None:
        assert self.pipeline and self._source
        target = 1.0 / max(self.settings.target_fps, 1)
        while not self._stop.is_set():
            started = time.time()
            try:
                if self.demo_mode and isinstance(self._source, DemoSource):
                    ok, frame = True, self.pipeline.demo.frame(utcnow()) if self.pipeline.demo else self._source.read()[1]
                else:
                    ok, frame = self._source.read()
                if not ok or frame is None:
                    time.sleep(0.05)
                    continue
                ts = utcnow()
                output = self.pipeline.process(frame, ts, self.settings.camera_id)
                self._maybe_demo_speech(output)
                payload = self._to_ws(output)
                self.latest_frame = payload
                self.latest_people = output.people
                self.fps = output.fps
                self.width = output.width
                self.height = output.height
                self._persist(output)
                self._emit(payload)
            except Exception as exc:
                logger.exception("pipeline error", extra={"event": "error", "error": str(exc)})
                self.message = f"Pipeline error: {exc}"
            elapsed = time.time() - started
            time.sleep(max(0.0, target - elapsed))

    def _maybe_demo_speech(self, output: PipelineOutput) -> None:
        if not (self.demo_mode and self.audio.enabled) or self._demo_speech_fired:
            return
        if self.pipeline and self.pipeline.demo:
            t = self.pipeline.demo.elapsed(output.timestamp)
            if 39 <= t < 41 and output.people:
                from app.events.engine import Event

                seg = self.audio.simulate_speech()
                text = seg.text if seg else "[simulated transcript]"
                output.events.append(
                    Event(
                        type=EventType.SPEECH_DETECTED,
                        timestamp=output.timestamp,
                        camera_id=self.settings.camera_id,
                        person_id=output.people[0]["person_id"],
                        demo=True,
                        metadata={"label": "Speech detected", "transcript": text},
                    )
                )
                self._demo_speech_fired = True

    def _to_ws(self, output: PipelineOutput) -> dict[str, Any]:
        return {
            "type": "frame",
            "timestamp": output.timestamp.isoformat(),
            "camera_id": output.camera_id,
            "fps": output.fps,
            "device": output.model_status.device,
            "demo_mode": output.demo,
            "simulated": output.demo,
            "width": output.width,
            "height": output.height,
            "jpeg_base64": base64.b64encode(output.jpeg).decode("ascii"),
            "people": output.people,
            "events": [
                {
                    "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                    "timestamp": e.timestamp.isoformat(),
                    "person_id": e.person_id,
                    "zone_id": e.zone_id,
                    "confidence": e.confidence,
                    "metadata": e.metadata,
                    "demo": e.demo,
                }
                for e in output.events
            ],
            "model_status": output.model_status.as_dict(),
            "microphone": self.audio.status_label,
            "reconstruction": {
                p["person_id"]: self.pipeline.recon.payload(p["person_id"], p.get("objects"))
                for p in output.people
            }
            if self.pipeline
            else {},
        }

    def _persist(self, output: PipelineOutput) -> None:
        now = time.time()
        # Persist events always; sample detections to keep SQLite light.
        persist_dets = now - self._last_persist >= 0.7
        db = SessionLocal()
        try:
            for person in output.people:
                repo.upsert_person(
                    db,
                    person["person_id"],
                    output.camera_id,
                    output.timestamp,
                    demo=person.get("demo", False),
                )
                if persist_dets:
                    from app.database import models
                    from sqlalchemy import select

                    open_row = db.scalar(
                        select(models.PersonSession).where(
                            models.PersonSession.person_id == person["person_id"],
                            models.PersonSession.status == "open",
                        )
                    )
                    if open_row is None:
                        repo.open_session(db, person["person_id"], output.camera_id, person.get("first_seen") and output.timestamp or output.timestamp)
                    repo.add_detection(
                        db,
                        person_id=person["person_id"],
                        camera_id=output.camera_id,
                        timestamp=output.timestamp,
                        confidence=person["confidence"],
                        bbox=person["bbox"],
                        zone_id=person.get("zone_id"),
                        demo=person.get("demo", False),
                    )
                    if person.get("face_landmarks"):
                        repo.add_face(
                            db,
                            person["person_id"],
                            output.timestamp,
                            {
                                "confidence": person["confidence"],
                                "bbox": person.get("face_bbox") or [],
                                "yaw": person.get("yaw"),
                                "pitch": person.get("pitch"),
                                "roll": person.get("roll"),
                                "landmarks": person.get("face_landmarks"),
                            },
                        )
                    if person.get("pose_landmarks"):
                        repo.add_pose(
                            db,
                            person["person_id"],
                            output.timestamp,
                            {
                                "orientation": person.get("orientation"),
                                "yaw": person.get("yaw"),
                                "landmarks": person.get("pose_landmarks"),
                                "confidence": person["confidence"],
                            },
                        )
                    repo.add_clothing(db, person["person_id"], output.timestamp, person.get("attributes") or {})
                    for obj in person.get("objects") or []:
                        repo.add_object(
                            db,
                            person_id=person["person_id"],
                            camera_id=output.camera_id,
                            timestamp=output.timestamp,
                            object_name=obj["object"],
                            confidence=obj["confidence"],
                            bbox=obj["bbox"],
                        )
                    if self.pipeline:
                        repo.add_reconstruction(
                            db,
                            person["person_id"],
                            output.timestamp,
                            self.pipeline.recon.payload(person["person_id"], person.get("objects")),
                        )
            for event in output.events:
                repo.add_timeline_event(
                    db,
                    event_type=str(event.type),
                    timestamp=event.timestamp,
                    camera_id=event.camera_id,
                    person_id=event.person_id,
                    zone_id=event.zone_id,
                    confidence=event.confidence,
                    metadata=event.metadata,
                    demo=event.demo,
                )
                if str(event.type) == EventType.PERSON_ENTERED and event.person_id:
                    repo.open_session(db, event.person_id, event.camera_id, event.timestamp)
                if str(event.type) == EventType.PERSON_EXITED and event.person_id:
                    repo.close_person(db, event.person_id, event.timestamp)
                    repo.close_open_session(db, event.person_id, event.timestamp)
                    if self.pipeline:
                        self.pipeline.recon.drop(event.person_id)
                if str(event.type) == EventType.SPEECH_DETECTED:
                    from app.database import models

                    audio_id = str(uuid.uuid4())
                    db.add(
                        models.AudioEvent(
                            id=audio_id,
                            timestamp=event.timestamp,
                            camera_id=event.camera_id,
                            person_id=event.person_id,
                            duration_seconds=1.0,
                            vad_confidence=0.9,
                        )
                    )
                    db.add(
                        models.Transcription(
                            audio_event_id=audio_id,
                            timestamp=event.timestamp,
                            text=str((event.metadata or {}).get("transcript", "")),
                            confidence=0.7,
                            engine=self.audio.engine,
                        )
                    )
            db.commit()
            if persist_dets:
                self._last_persist = now
        except Exception as exc:
            db.rollback()
            logger.warning("persist failed", extra={"event": "error", "error": str(exc)})
        finally:
            db.close()

    def _emit(self, payload: dict[str, Any]) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), self._loop)


runtime = CameraRuntime()
