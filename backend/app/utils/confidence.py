"""Confidence thresholding. Uncertain predictions become UNKNOWN, not facts."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")

UNKNOWN = "UNKNOWN"


def accept(value: T, confidence: float, threshold: float) -> T | str:
    if confidence < threshold:
        return UNKNOWN
    return value


def is_known(value: str | None) -> bool:
    return bool(value) and value != UNKNOWN
