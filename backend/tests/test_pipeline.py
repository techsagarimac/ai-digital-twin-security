from datetime import datetime, timezone

import numpy as np

from app.config import get_settings
from app.vision.pipeline import VisionPipeline


def test_demo_pipeline_produces_simulated_person() -> None:
    settings = get_settings()
    pipe = VisionPipeline(settings, demo_forced=True)
    ts = datetime(2026, 9, 4, 10, 32, 20, tzinfo=timezone.utc)
    if pipe.demo:
        pipe.demo.t0 = datetime(2026, 9, 4, 10, 32, 0, tzinfo=timezone.utc)
        frame = pipe.demo.frame(ts)
    else:
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
    out = pipe.process(frame, ts, "cam-1")
    assert out.demo is True
    assert out.model_status.detector.startswith("mock")
    # At t=20s into the scenario a person should be present.
    assert len(out.people) == 1
    person = out.people[0]
    assert person["person_id"] == "P001"
    assert person["simulated"] is True
    assert person["bbox"][2] > person["bbox"][0]
    assert out.jpeg[:2] == b"\xff\xd8"
