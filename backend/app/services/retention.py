"""Configurable data retention. Default is 7 days — not indefinite."""

from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.database import repositories as repo
from app.database.database import SessionLocal
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def purge_expired() -> dict[str, int]:
    settings = get_settings()
    db = SessionLocal()
    try:
        counts = repo.purge_older_than(db, settings.data_retention_days)
        db.commit()
    finally:
        db.close()
    cutoff = utcnow().timestamp() - settings.data_retention_days * 86400
    files = 0
    for folder in (settings.recordings_dir, settings.audio_dir, settings.reconstructions_dir, settings.upload_dir):
        for path in Path(folder).glob("*"):
            if path.name == ".gitkeep":
                continue
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    files += 1
            except OSError:
                continue
    counts["files"] = files
    logger.info("retention cleanup", extra={"event": "retention_cleanup", "error": None})
    return counts
