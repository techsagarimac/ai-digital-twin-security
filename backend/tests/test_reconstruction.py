from datetime import datetime, timezone

from app.utils.geometry import BBox
from app.vision.reconstruction import ReconstructionFuser, yaw_to_view
from app.vision.types import FaceResult, Landmark, PoseResult


def _pose(yaw: float) -> PoseResult:
    lms = [Landmark(i, float(i), float(i), 0.0, 0.8) for i in range(17)]
    return PoseResult(lms, "front-facing", yaw, 0.8)


def test_yaw_bins() -> None:
    assert yaw_to_view(0) == "front"
    assert yaw_to_view(90) == "right"
    assert yaw_to_view(180) == "back"
    assert yaw_to_view(-90) == "left"


def test_coverage_does_not_invent_unseen_views() -> None:
    fuser = ReconstructionFuser()
    ts = datetime.now(timezone.utc)
    fuser.update("P001", ts, _pose(0), None)
    fuser.update("P001", ts, _pose(90), None)
    payload = fuser.payload("P001")
    assert payload["coverage"] == 50.0
    assert payload["views"]["front"] is True
    assert payload["views"]["right"] is True
    assert payload["views"]["back"] is False
    assert payload["views"]["left"] is False
    assert any("Back view unavailable" in item for item in payload["insufficient"])
    assert payload["label"] == "Estimated 3D Model"
