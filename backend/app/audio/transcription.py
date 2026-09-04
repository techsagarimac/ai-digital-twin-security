"""Optional microphone path. Never starts unless AUDIO_ENABLED and the operator turns it on."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SpeechSegment:
    timestamp: datetime
    duration_seconds: float
    text: str
    confidence: float
    engine: str
    vad_confidence: float


class BaseSpeechProcessor(ABC):
    name = "base"

    @abstractmethod
    def transcribe(self, audio: bytes, sample_rate: int) -> SpeechSegment | None:
        raise NotImplementedError


class UnavailableSpeechProcessor(BaseSpeechProcessor):
    name = "unavailable"

    def transcribe(self, audio: bytes, sample_rate: int) -> SpeechSegment | None:
        return None


class MockSpeechProcessor(BaseSpeechProcessor):
    name = "mock"

    def transcribe(self, audio: bytes, sample_rate: int) -> SpeechSegment | None:
        from app.utils.time import utcnow

        return SpeechSegment(
            timestamp=utcnow(),
            duration_seconds=1.2,
            text="[simulated transcript] security check complete",
            confidence=0.7,
            engine="mock",
            vad_confidence=0.9,
        )


class WhisperSpeechProcessor(BaseSpeechProcessor):
    name = "whisper"

    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel("tiny", device="cpu")

    def transcribe(self, audio: bytes, sample_rate: int) -> SpeechSegment | None:
        import io
        import wave

        from app.utils.time import utcnow

        buf = io.BytesIO(audio)
        try:
            with wave.open(buf, "rb") as wav:
                frames = wav.readframes(wav.getnframes())
                rate = wav.getframerate()
        except Exception:
            return None
        # faster-whisper wants a file path or numpy; keep a tiny adapter.
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
        tmp.write_bytes(audio)
        try:
            segments, _info = self._model.transcribe(str(tmp))
            text = " ".join(s.text.strip() for s in segments).strip()
        finally:
            tmp.unlink(missing_ok=True)
        if not text:
            return None
        return SpeechSegment(utcnow(), 0.0, text, 0.7, "whisper", 0.8)


def create_speech_processor(demo: bool = False) -> tuple[BaseSpeechProcessor, str]:
    if demo:
        return MockSpeechProcessor(), "mock (simulated)"
    try:
        proc = WhisperSpeechProcessor()
        logger.info("model loaded", extra={"event": "model_loaded", "model": "whisper"})
        return proc, "whisper"
    except Exception as exc:
        logger.warning("model unavailable", extra={"event": "model_unavailable", "model": "speech", "error": str(exc)})
        return UnavailableSpeechProcessor(), "unavailable"


class AudioGateway:
    """Records only when the operator has enabled the microphone."""

    def __init__(self) -> None:
        self.enabled = False
        self.recording = False
        self.status_label = "OFF"
        self.processor, self.engine = create_speech_processor(demo=False)
        self.last_error = ""
        if self.engine == "unavailable":
            self.last_error = "Speech transcription unavailable"

    def set_enabled(self, enabled: bool, demo: bool = False) -> None:
        self.enabled = enabled
        self.status_label = "ON" if enabled else "OFF"
        if enabled:
            self.processor, self.engine = create_speech_processor(demo=demo)
            if self.engine == "unavailable":
                self.last_error = "Speech transcription unavailable"
            logger.info("audio processing started", extra={"event": "audio_processing_started"})
        else:
            self.recording = False
            logger.info("audio processing stopped", extra={"event": "audio_processing_stopped"})

    def simulate_speech(self):  # type: ignore[no-untyped-def]
        if not self.enabled:
            return None
        return self.processor.transcribe(b"", 16000)
