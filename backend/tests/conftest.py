from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "_twin_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["AUTH_ENABLED"] = "false"
os.environ["DEMO_MODE"] = "false"
os.environ["AUDIO_ENABLED"] = "false"
os.environ["DATA_RETENTION_DAYS"] = "7"

from app.config import reload_settings
from app.database.database import init_db, reset_engine

reload_settings()
reset_engine()
init_db()

import pytest


@pytest.fixture
def db_session():
    from app.database.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
