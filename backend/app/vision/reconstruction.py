"""Progressive estimated-3D fusion. Unseen views stay empty — no hallucinated geometry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.vision.pose import SKELETON_EDGES
from app.vision.types import FaceResult, Landmark, PoseResult

VIEWS = ("front", "right", "back", "left")


def yaw_to_view(yaw: float | None) -> str | None:
    if yaw is None:
        return None
    wrapped = ((yaw + 180) % 360) - 180
    if -45 <= wrapped < 45:
        return "front"
    if 45 <= wrapped < 135:
        return "right"
    if wrapped >= 135 or wrapped < -135:
        return "back"
    return "left"


def orientation_to_view(orientation: str) -> str | None:
    mapping = {
        "front-facing": "front",
        "right-facing": "right",
        "back-facing": "back",
        "left-facing": "left",
    }
    return mapping.get(orientation)


@dataclass
class ViewBin:
    count: int = 0
    pose: dict[int, Landmark] = field(default_factory=dict)
    face: dict[int, Landmark] = field(default_factory=dict)
    yaw_sum: float = 0.0
    pitch_sum: float = 0.0
    roll_sum: float = 0.0
    conf_sum: float = 0.0
    last_seen: datetime | None = None

    def observed(self) -> bool:
        return self.count > 0


@dataclass
class ReconstructionState:
    person_id: str
    bins: dict[str, ViewBin] = field(default_factory=lambda: {name: ViewBin() for name in VIEWS})
    latest_pose: list[Landmark] = field(default_factory=list)
    latest_face: list[Landmark] = field(default_factory=list)
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None

    @property
    def coverage(self) -> float:
        observed = sum(1 for b in self.bins.values() if b.observed())
        return round(100.0 * observed / len(VIEWS), 1)

    def views_flags(self) -> dict[str, bool]:
        return {name: self.bins[name].observed() for name in VIEWS}

    def insufficient(self) -> list[str]:
        labels = {"front": "Front view unavailable", "left": "Left view unavailable", "right": "Right view unavailable", "back": "Back view unavailable"}
        return [labels[name] for name, bin_ in self.bins.items() if not bin_.observed()]

    def mesh_confidence(self) -> float:
        total = sum(b.count for b in self.bins.values())
        if total == 0:
            return 0.0
        weighted = sum(b.conf_sum for b in self.bins.values()) / max(total, 1)
        return round(min(0.95, 0.35 + 0.15 * sum(1 for b in self.bins.values() if b.observed()) + weighted * 0.2), 3)

    def fused_pose(self) -> list[Landmark]:
        # Prefer the most recently updated observed bin; do not invent missing views.
        newest: ViewBin | None = None
        for bin_ in self.bins.values():
            if not bin_.observed():
                continue
            if newest is None or (bin_.last_seen and newest.last_seen and bin_.last_seen > newest.last_seen):
                newest = bin_
            elif newest is None:
                newest = bin_
        if newest and newest.pose:
            return list(newest.pose.values())
        return self.latest_pose

    def fused_face(self) -> list[Landmark]:
        newest: ViewBin | None = None
        for bin_ in self.bins.values():
            if not bin_.observed() or not bin_.face:
                continue
            if newest is None or (bin_.last_seen and newest.last_seen and bin_.last_seen > newest.last_seen):
                newest = bin_
        if newest:
            return list(newest.face.values())
        return self.latest_face


class ReconstructionFuser:
    def __init__(self) -> None:
        self._states: dict[str, ReconstructionState] = {}

    def reset(self) -> None:
        self._states.clear()

    def drop(self, person_id: str) -> None:
        self._states.pop(person_id, None)

    def get(self, person_id: str) -> ReconstructionState | None:
        return self._states.get(person_id)

    def update(
        self,
        person_id: str,
        timestamp: datetime,
        pose: PoseResult | None,
        face: FaceResult | None,
    ) -> ReconstructionState:
        state = self._states.setdefault(person_id, ReconstructionState(person_id=person_id))
        yaw = None
        if face and face.yaw is not None:
            yaw = face.yaw
            state.pitch = face.pitch
            state.roll = face.roll
        if pose and pose.yaw is not None and yaw is None:
            yaw = pose.yaw
        if yaw is not None:
            state.yaw = yaw
        view = yaw_to_view(yaw) or (orientation_to_view(pose.orientation) if pose else None)
        if view is None:
            return state
        bin_ = state.bins[view]
        bin_.count += 1
        bin_.last_seen = timestamp
        conf = 0.0
        if pose:
            state.latest_pose = pose.landmarks
            _blend(bin_.pose, pose.landmarks)
            conf = max(conf, pose.confidence)
        if face:
            state.latest_face = face.mesh or face.landmarks
            _blend(bin_.face, face.mesh or face.landmarks)
            conf = max(conf, face.confidence)
            if face.yaw is not None:
                bin_.yaw_sum += face.yaw
            if face.pitch is not None:
                bin_.pitch_sum += face.pitch
            if face.roll is not None:
                bin_.roll_sum += face.roll
        bin_.conf_sum += conf
        return state

    def payload(self, person_id: str, objects: list[dict] | None = None) -> dict:
        state = self._states.get(person_id) or ReconstructionState(person_id=person_id)
        flags = state.views_flags()
        return {
            "person_id": person_id,
            "label": "Estimated 3D Model",
            "disclaimer": "AI-generated geometry from visible landmarks. Not a medical, physical, or X-ray scan.",
            "coverage": state.coverage,
            "views": {
                "front_view": flags["front"],
                "left_view": flags["left"],
                "right_view": flags["right"],
                "back_view": flags["back"],
                "front": flags["front"],
                "left": flags["left"],
                "right": flags["right"],
                "back": flags["back"],
            },
            "mesh_confidence": state.mesh_confidence(),
            "insufficient": state.insufficient(),
            "pose_landmarks": [lm.as_dict() for lm in state.fused_pose()],
            "face_landmarks": [lm.as_dict() for lm in state.fused_face()],
            "skeleton_edges": SKELETON_EDGES,
            "objects": objects or [],
            "yaw": state.yaw,
            "pitch": state.pitch,
            "roll": state.roll,
        }


def _blend(store: dict[int, Landmark], incoming: list[Landmark]) -> None:
    for lm in incoming:
        prev = store.get(lm.id)
        if prev is None:
            store[lm.id] = Landmark(lm.id, lm.x, lm.y, lm.z, lm.confidence)
            continue
        w_old, w_new = 0.7, 0.3
        store[lm.id] = Landmark(
            lm.id,
            prev.x * w_old + lm.x * w_new,
            prev.y * w_old + lm.y * w_new,
            prev.z * w_old + lm.z * w_new,
            max(prev.confidence, lm.confidence),
        )
