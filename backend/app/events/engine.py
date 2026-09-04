"""Diff previous vs current person state into timeline events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.events.types import EventType


@dataclass(slots=True)
class Event:
    type: EventType
    timestamp: datetime
    camera_id: str
    person_id: str | None = None
    zone_id: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    demo: bool = False


@dataclass
class PersonSnapshot:
    person_id: str
    zone_id: str | None
    has_face: bool
    objects: set[str]
    orientation: str
    coverage: float
    demo: bool = False


class EventEngine:
    def __init__(self) -> None:
        self._prev: dict[str, PersonSnapshot] = {}
        self._last_coverage: dict[str, float] = {}
        self._seen_objects: dict[str, set[str]] = {}

    def reset(self) -> None:
        self._prev.clear()
        self._last_coverage.clear()
        self._seen_objects.clear()

    def diff(
        self,
        current: list[PersonSnapshot],
        timestamp: datetime,
        camera_id: str,
        closed_ids: list[str],
    ) -> list[Event]:
        events: list[Event] = []
        current_map = {item.person_id: item for item in current}

        for person_id, snap in current_map.items():
            prev = self._prev.get(person_id)
            if prev is None:
                events.append(
                    Event(
                        type=EventType.PERSON_ENTERED,
                        timestamp=timestamp,
                        camera_id=camera_id,
                        person_id=person_id,
                        zone_id=snap.zone_id,
                        demo=snap.demo,
                        metadata={"label": "Person detected"},
                    )
                )
                events.append(
                    Event(
                        type=EventType.TRACKING_STARTED,
                        timestamp=timestamp,
                        camera_id=camera_id,
                        person_id=person_id,
                        demo=snap.demo,
                        metadata={"label": "Tracking started"},
                    )
                )
                if snap.zone_id:
                    events.append(
                        Event(
                            type=EventType.ZONE_ENTERED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            zone_id=snap.zone_id,
                            demo=snap.demo,
                            metadata={"label": f"Entered {snap.zone_id}"},
                        )
                    )
                self._seen_objects[person_id] = set()
                for name in sorted(snap.objects):
                    self._seen_objects[person_id].add(name)
                    events.append(
                        Event(
                            type=EventType.OBJECT_DETECTED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            demo=snap.demo,
                            metadata={"label": f"{name} detected", "object": name},
                        )
                    )
            else:
                if prev.zone_id != snap.zone_id:
                    if prev.zone_id:
                        events.append(
                            Event(
                                type=EventType.ZONE_EXITED,
                                timestamp=timestamp,
                                camera_id=camera_id,
                                person_id=person_id,
                                zone_id=prev.zone_id,
                                demo=snap.demo,
                                metadata={"label": f"Left {prev.zone_id}"},
                            )
                        )
                    if snap.zone_id:
                        events.append(
                            Event(
                                type=EventType.ZONE_ENTERED,
                                timestamp=timestamp,
                                camera_id=camera_id,
                                person_id=person_id,
                                zone_id=snap.zone_id,
                                demo=snap.demo,
                                metadata={"label": f"Entered {snap.zone_id}"},
                            )
                        )
                if snap.has_face and not prev.has_face:
                    events.append(
                        Event(
                            type=EventType.FACE_DETECTED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            demo=snap.demo,
                            metadata={"label": "Face detected"},
                        )
                    )
                seen = self._seen_objects.setdefault(person_id, set())
                new_objects = snap.objects - seen
                seen.update(snap.objects)
                for name in sorted(new_objects):
                    events.append(
                        Event(
                            type=EventType.OBJECT_DETECTED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            demo=snap.demo,
                            metadata={"label": f"{name} detected", "object": name},
                        )
                    )
                if snap.orientation != prev.orientation and snap.orientation != "UNKNOWN":
                    events.append(
                        Event(
                            type=EventType.POSE_CHANGED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            demo=snap.demo,
                            metadata={"label": f"Person {snap.orientation.replace('_', ' ')}", "orientation": snap.orientation},
                        )
                    )
                    events.append(
                        Event(
                            type=EventType.VIEW_ANGLE_UPDATED,
                            timestamp=timestamp,
                            camera_id=camera_id,
                            person_id=person_id,
                            demo=snap.demo,
                            metadata={"label": "View angle updated", "orientation": snap.orientation},
                        )
                    )

            last_cov = self._last_coverage.get(person_id, -1)
            if snap.coverage >= last_cov + 8:
                events.append(
                    Event(
                        type=EventType.RECONSTRUCTION_UPDATED,
                        timestamp=timestamp,
                        camera_id=camera_id,
                        person_id=person_id,
                        demo=snap.demo,
                        metadata={"label": "Reconstruction updated", "coverage": snap.coverage},
                    )
                )
                self._last_coverage[person_id] = snap.coverage

        for person_id in closed_ids:
            prev = self._prev.get(person_id)
            events.append(
                Event(
                    type=EventType.TRACKING_ENDED,
                    timestamp=timestamp,
                    camera_id=camera_id,
                    person_id=person_id,
                    zone_id=prev.zone_id if prev else None,
                    demo=prev.demo if prev else False,
                    metadata={"label": "Tracking ended"},
                )
            )
            events.append(
                Event(
                    type=EventType.PERSON_EXITED,
                    timestamp=timestamp,
                    camera_id=camera_id,
                    person_id=person_id,
                    zone_id=prev.zone_id if prev else None,
                    demo=prev.demo if prev else False,
                    metadata={"label": "Person left camera"},
                )
            )
            self._prev.pop(person_id, None)
            self._seen_objects.pop(person_id, None)

        self._prev = current_map
        return events
