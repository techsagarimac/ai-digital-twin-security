from datetime import datetime, timezone

from app.audio.recorder import energy_vad
from app.audio.transcription import MockSpeechProcessor
from app.identity.module import IdentityDisabledError, IdentityModule
from app.utils.time import format_duration


def test_identity_disabled_by_default() -> None:
    mod = IdentityModule(enabled=False, consent=False)
    try:
        mod.identify(None)
        raise AssertionError("should have refused")
    except IdentityDisabledError:
        pass


def test_vad_and_mock_speech() -> None:
    active, conf = energy_vad([0.5, 0.4, 0.6])
    assert active is True
    silent, _ = energy_vad([0.0, 0.0, 0.0])
    assert silent is False
    seg = MockSpeechProcessor().transcribe(b"", 16000)
    assert seg is not None
    assert "simulated" in seg.text


def test_format_duration() -> None:
    assert format_duration(14 * 60 + 49) == "14m 49s"
    assert format_duration(4 * 60 + 32) == "4m 32s"
