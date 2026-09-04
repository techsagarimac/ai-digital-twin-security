"""Voice activity placeholder. Real capture only happens when the mic is ON."""

from __future__ import annotations


def energy_vad(samples: list[float], threshold: float = 0.02) -> tuple[bool, float]:
    if not samples:
        return False, 0.0
    energy = sum(abs(x) for x in samples) / len(samples)
    return energy >= threshold, float(min(1.0, energy / max(threshold, 1e-6)))
