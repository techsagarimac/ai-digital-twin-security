from datetime import datetime, timedelta, timezone

from app.utils.geometry import BBox
from app.vision.tracker import PersonTracker, compute_duration
from app.vision.types import Detection


def ts(seconds: float = 0) -> datetime:
    return datetime(2026, 9, 4, 10, 32, 14, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_assigns_person_ids_and_tracks_position() -> None:
    tracker = PersonTracker(timeout_seconds=5)
    d1 = Detection(BBox(10, 10, 50, 120), 0.94, "person")
    tracks = tracker.update([d1], ts(0))
    assert len(tracks) == 1
    assert tracks[0].person_id == "P001"
    d2 = Detection(BBox(20, 12, 60, 122), 0.91, "person")
    tracks = tracker.update([d2], ts(1))
    assert len(tracks) == 1
    assert tracks[0].person_id == "P001"
    assert tracks[0].observation_count == 2
    assert tracks[0].vx != 0


def test_timeout_closes_session() -> None:
    tracker = PersonTracker(timeout_seconds=5)
    tracker.update([Detection(BBox(0, 0, 40, 80), 0.9, "person")], ts(0))
    tracker.update([], ts(6))
    closed = tracker.pop_closed()
    assert len(closed) == 1
    assert closed[0].person_id == "P001"
    assert tracker.active() == []


def test_two_people_get_distinct_ids() -> None:
    tracker = PersonTracker()
    tracks = tracker.update(
        [
            Detection(BBox(0, 0, 40, 80), 0.9, "person"),
            Detection(BBox(200, 0, 240, 80), 0.88, "person"),
        ],
        ts(0),
    )
    ids = {t.person_id for t in tracks}
    assert ids == {"P001", "P002"}


def test_duration_calculation() -> None:
    first = ts(0)
    last = ts(14 * 60 + 49)
    assert compute_duration(first, last) == 14 * 60 + 49
