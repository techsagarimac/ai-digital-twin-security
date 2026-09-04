"""IoU multi-object tracker with velocity and session timeout."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.utils.geometry import BBox
from app.utils.ids import format_person_id
from app.utils.time import duration_seconds
from app.vision.types import Detection, Track


class PersonTracker:
    def __init__(self, timeout_seconds: float = 5.0, iou_threshold: float = 0.3) -> None:
        self.timeout_seconds = timeout_seconds
        self.iou_threshold = iou_threshold
        self._tracks: dict[str, Track] = {}
        self._next_index = 1
        self._closed: list[Track] = []

    @property
    def tracks(self) -> dict[str, Track]:
        return self._tracks

    def active(self) -> list[Track]:
        return list(self._tracks.values())

    def pop_closed(self) -> list[Track]:
        closed = self._closed
        self._closed = []
        return closed

    def reset(self) -> None:
        self._tracks.clear()
        self._closed.clear()
        self._next_index = 1

    def update(self, detections: list[Detection], timestamp: datetime) -> list[Track]:
        unmatched_tracks = set(self._tracks.keys())
        unmatched_dets = list(range(len(detections)))
        pairs: list[tuple[float, str, int]] = []
        for track_id, track in self._tracks.items():
            for idx, det in enumerate(detections):
                pairs.append((track.bbox.iou(det.bbox), track_id, idx))
        pairs.sort(reverse=True)

        used_tracks: set[str] = set()
        used_dets: set[int] = set()
        for iou, track_id, idx in pairs:
            if iou < self.iou_threshold:
                break
            if track_id in used_tracks or idx in used_dets:
                continue
            self._apply(self._tracks[track_id], detections[idx], timestamp)
            used_tracks.add(track_id)
            used_dets.add(idx)
            unmatched_tracks.discard(track_id)

        for idx in unmatched_dets:
            if idx in used_dets:
                continue
            det = detections[idx]
            person_id = format_person_id(self._next_index)
            self._next_index += 1
            self._tracks[person_id] = Track(
                person_id=person_id,
                bbox=det.bbox,
                confidence=det.confidence,
                first_seen=timestamp,
                last_seen=timestamp,
                simulated=det.simulated,
            )

        timeout = timedelta(seconds=self.timeout_seconds)
        expired: list[str] = []
        for track_id in unmatched_tracks:
            track = self._tracks[track_id]
            track.misses += 1
            if timestamp - track.last_seen >= timeout:
                expired.append(track_id)
        for track_id in expired:
            closed = self._tracks.pop(track_id)
            self._closed.append(closed)

        return self.active()

    def _apply(self, track: Track, det: Detection, timestamp: datetime) -> None:
        dt = max(duration_seconds(track.last_seen, timestamp), 1e-3)
        prev_cx, prev_cy = track.bbox.centroid
        new_cx, new_cy = det.bbox.centroid
        track.vx = (new_cx - prev_cx) / dt
        track.vy = (new_cy - prev_cy) / dt
        track.bbox = det.bbox
        track.confidence = det.confidence
        track.last_seen = timestamp
        track.observation_count += 1
        track.hits += 1
        track.misses = 0
        track.simulated = det.simulated


def compute_duration(first_seen: datetime, last_seen: datetime) -> float:
    return duration_seconds(first_seen, last_seen)
