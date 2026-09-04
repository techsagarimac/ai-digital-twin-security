"""Persistent tables for the security prototype. Timestamps are UTC."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base
from app.utils.time import utcnow


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(32), default="active")
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    demo: Mapped[int] = mapped_column(Integer, default=0)


class PersonSession(Base):
    __tablename__ = "person_sessions"
    __table_args__ = (Index("ix_sessions_person_start", "person_id", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"), index=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="open")


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (Index("ix_detections_ts", "timestamp"), Index("ix_detections_person", "person_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[str] = mapped_column(Text)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    demo: Mapped[int] = mapped_column(Integer, default=0)


class FaceObservation(Base):
    __tablename__ = "face_observations"
    __table_args__ = (Index("ix_face_person_ts", "person_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[str] = mapped_column(Text)
    yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    landmarks_json: Mapped[str] = mapped_column(Text, default="[]")


class LandmarkObservation(Base):
    __tablename__ = "landmark_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    kind: Mapped[str] = mapped_column(String(32))
    landmark_id: Mapped[int] = mapped_column(Integer)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    z: Mapped[float] = mapped_column(Float, default=0.0)
    view_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class ObjectDetection(Base):
    __tablename__ = "object_detections"
    __table_args__ = (Index("ix_objects_person_ts", "person_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    object_name: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[str] = mapped_column(Text)


class ClothingObservation(Base):
    __tablename__ = "clothing_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    top_label: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    top_color: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    top_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    bottom_label: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    bottom_color: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    bottom_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    shoes_label: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    shoes_color: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    shoes_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    hair_presence: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    hair_color: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    hair_style: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    hair_length: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    hair_confidence: Mapped[float] = mapped_column(Float, default=0.0)


class PoseObservation(Base):
    __tablename__ = "pose_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    orientation: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    landmarks_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class ReconstructionObservation(Base):
    __tablename__ = "reconstruction_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    coverage: Mapped[float] = mapped_column(Float, default=0.0)
    front_view: Mapped[int] = mapped_column(Integer, default=0)
    left_view: Mapped[int] = mapped_column(Integer, default=0)
    right_view: Mapped[int] = mapped_column(Integer, default=0)
    back_view: Mapped[int] = mapped_column(Integer, default=0)
    mesh_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        Index("ix_events_ts", "timestamp"),
        Index("ix_events_person", "person_id"),
        Index("ix_events_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    demo: Mapped[int] = mapped_column(Integer, default=0)


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)
    color: Mapped[str] = mapped_column(String(16), default="#3ee0c5")


class AudioEvent(Base):
    __tablename__ = "audio_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    person_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    vad_confidence: Mapped[float] = mapped_column(Float, default=0.0)


class Transcription(Base):
    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audio_event_id: Mapped[str] = mapped_column(ForeignKey("audio_events.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    engine: Mapped[str] = mapped_column(String(64), default="unavailable")


class CameraSession(Base):
    __tablename__ = "camera_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(256))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    demo: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="running")


class VisibleFeature(Base):
    """Neutral visible-feature marks. Not medical claims. Operators may correct/remove."""

    __tablename__ = "visible_features"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(16), index=True)
    feature_type: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(64), default="UNKNOWN")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    frame_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    suppressed: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
