from datetime import datetime, timedelta, timezone

from app.database import models
from app.database import repositories as repo
from app.database.database import SessionLocal
from app.utils.time import utcnow


def test_person_and_event_roundtrip() -> None:
    db = SessionLocal()
    try:
        ts = datetime.now(timezone.utc)
        repo.upsert_person(db, "P001", "cam-1", ts, demo=False)
        repo.add_timeline_event(
            db,
            event_type="PERSON_ENTERED",
            timestamp=ts,
            camera_id="cam-1",
            person_id="P001",
            metadata={"label": "Person detected"},
        )
        db.commit()
        person = db.get(models.Person, "P001")
        assert person is not None
        assert person.camera_id == "cam-1"
    finally:
        db.close()


def test_retention_deletes_old_events() -> None:
    db = SessionLocal()
    try:
        old = utcnow() - timedelta(days=30)
        repo.add_timeline_event(
            db,
            event_type="PERSON_EXITED",
            timestamp=old,
            camera_id="cam-1",
            person_id="P099",
            metadata={"label": "old"},
        )
        db.commit()
        counts = repo.purge_older_than(db, days=7)
        db.commit()
        assert counts.get("timeline_events", 0) >= 1
    finally:
        db.close()
