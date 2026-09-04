"""Inference device selection. CUDA is optional."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(preference: str = "auto") -> str:
    pref = (preference or "auto").lower()
    if pref in {"cpu", "cuda"}:
        if pref == "cuda" and not _cuda_available():
            logger.warning("cuda requested but unavailable; using cpu")
            return "cpu"
        return pref
    return "cuda" if _cuda_available() else "cpu"


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False
