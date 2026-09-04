from datetime import datetime, timezone

from app.events.engine import EventEngine, PersonSnapshot
from app.events.types import EventType


def test_enter_exit_and_zone_events() -> None:
    engine = EventEngine()
    ts = datetime(2026, 9, 4, 10, 32, 14, tzinfo=timezone.utc)
    first = [
        PersonSnapshot("P001", "zone-a", False, set(), "UNKNOWN", 0.0),
    ]
    events = engine.diff(first, ts, "cam-1", [])
    types = [e.type for e in events]
    assert EventType.PERSON_ENTERED in types
    assert EventType.ZONE_ENTERED in types

    second = [
        PersonSnapshot("P001", "zone-b", True, {"glasses"}, "left-facing", 25.0),
    ]
    events = engine.diff(second, ts, "cam-1", [])
    types = [e.type for e in events]
    assert EventType.ZONE_EXITED in types
    assert EventType.ZONE_ENTERED in types
    assert EventType.FACE_DETECTED in types
    assert EventType.OBJECT_DETECTED in types
    assert EventType.POSE_CHANGED in types

    events = engine.diff([], ts, "cam-1", ["P001"])
    types = [e.type for e in events]
    assert EventType.PERSON_EXITED in types
    assert EventType.TRACKING_ENDED in types
