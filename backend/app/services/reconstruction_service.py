"""Reconstruction payloads for the 3D viewer."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import models
from app.services.camera_service import runtime


def get_reconstruction(db: Session, person_id: str) -> dict[str, Any] | None:
    if runtime.pipeline:
        live = runtime.pipeline.recon.get(person_id)
        if live:
            person = next((p for p in runtime.latest_people if p["person_id"] == person_id), None)
            return runtime.pipeline.recon.payload(person_id, (person or {}).get("objects"))
    row = db.scalar(
        select(models.ReconstructionObservation)
        .where(models.ReconstructionObservation.person_id == person_id)
        .order_by(models.ReconstructionObservation.timestamp.desc())
    )
    if row is None:
        return None
    return json.loads(row.payload_json)
