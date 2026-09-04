"""Camera source adapters: webcam, uploaded video, RTSP plugin, demo frames."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class BaseCameraSource(ABC):
    name = "base"

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @property
    def size(self) -> tuple[int, int]:
        return (0, 0)


class WebcamSource(BaseCameraSource):
    name = "webcam"

    def __init__(self, index: int = 0) -> None:
        self.index = index
        self._cap: cv2.VideoCapture | None = None
        self._size = (0, 0)

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            raise RuntimeError(f"webcam {self.index} could not be opened")
        self._size = (
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480),
        )
        logger.info("camera started", extra={"event": "camera_started", "camera_id": f"webcam:{self.index}"})

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None
        return self._cap.read()

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("camera stopped", extra={"event": "camera_stopped", "camera_id": f"webcam:{self.index}"})

    @property
    def size(self) -> tuple[int, int]:
        return self._size


class VideoFileSource(BaseCameraSource):
    name = "video"

    def __init__(self, path: str, loop: bool = True) -> None:
        self.path = path
        self.loop = loop
        self._cap: cv2.VideoCapture | None = None
        self._size = (0, 0)

    def open(self) -> None:
        if not Path(self.path).exists():
            raise FileNotFoundError(self.path)
        self._cap = cv2.VideoCapture(self.path)
        if not self._cap.isOpened():
            raise RuntimeError(f"video could not be opened: {self.path}")
        self._size = (
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480),
        )
        logger.info("camera started", extra={"event": "camera_started", "camera_id": self.path})

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None:
            return False, None
        ok, frame = self._cap.read()
        if not ok and self.loop:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self._cap.read()
        return ok, frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("camera stopped", extra={"event": "camera_stopped", "camera_id": self.path})

    @property
    def size(self) -> tuple[int, int]:
        return self._size


class RTSPSource(BaseCameraSource):
    """Plugin adapter. Architecture is in place; URL is required to connect."""

    name = "rtsp"

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("rtsp url required")
        self.url = url
        self._inner = VideoFileSource(url, loop=False)

    def open(self) -> None:
        self._inner.path = self.url
        self._cap_open()

    def _cap_open(self) -> None:
        self._inner._cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if not self._inner._cap.isOpened():
            raise RuntimeError("RTSP camera could not be opened")
        self._inner._size = (
            int(self._inner._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640),
            int(self._inner._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480),
        )
        logger.info("camera started", extra={"event": "camera_started", "camera_id": "rtsp"})

    def read(self) -> tuple[bool, np.ndarray | None]:
        return self._inner.read()

    def close(self) -> None:
        self._inner.close()

    @property
    def size(self) -> tuple[int, int]:
        return self._inner.size


class PushFrameSource(BaseCameraSource):
    """Latest JPEG/frame pushed from the browser camera (macOS-friendly)."""

    name = "browser"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._size = (640, 480)
        self._open = False
        self._event = threading.Event()

    def open(self) -> None:
        self._open = True
        logger.info("camera started", extra={"event": "camera_started", "camera_id": "browser"})

    def push(self, frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            return
        with self._lock:
            self._frame = frame
            self._size = (int(frame.shape[1]), int(frame.shape[0]))
        self._event.set()

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._open:
            return False, None
        self._event.wait(timeout=0.4)
        self._event.clear()
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    def close(self) -> None:
        self._open = False
        self._event.set()
        logger.info("camera stopped", extra={"event": "camera_stopped", "camera_id": "browser"})

    @property
    def size(self) -> tuple[int, int]:
        return self._size


class DemoSource(BaseCameraSource):
    name = "demo"

    def __init__(self, scenario) -> None:  # type: ignore[no-untyped-def]
        self.scenario = scenario
        self._open = False

    def open(self) -> None:
        self._open = True
        logger.info("camera started", extra={"event": "camera_started", "camera_id": "demo"})

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._open:
            return False, None
        from app.utils.time import utcnow

        return True, self.scenario.frame(utcnow())

    def close(self) -> None:
        self._open = False
        logger.info("camera stopped", extra={"event": "camera_stopped", "camera_id": "demo"})

    @property
    def size(self) -> tuple[int, int]:
        return (self.scenario.width, self.scenario.height)
