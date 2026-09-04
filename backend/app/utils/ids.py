"""Temporary track IDs (P001…) — not biometric identities."""

from __future__ import annotations


def format_person_id(index: int) -> str:
    if index < 1:
        raise ValueError("person index must be >= 1")
    return f"P{index:03d}"


def parse_person_id(person_id: str) -> int:
    text = person_id.strip().upper()
    if not text.startswith("P"):
        raise ValueError("invalid person id")
    return int(text[1:])
