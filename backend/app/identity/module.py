"""Optional biometric identification — OFF by default, isolated, not implemented as search."""

from __future__ import annotations


class IdentityDisabledError(RuntimeError):
    pass


class IdentityModule:
    """Refuses to run unless both the env flag and explicit consent are set.

    No face gallery, no external database search, and no secret matching.
    """

    def __init__(self, enabled: bool, consent: bool) -> None:
        self.enabled = bool(enabled and consent)

    def identify(self, _embedding: object) -> None:
        if not self.enabled:
            raise IdentityDisabledError(
                "Biometric identification is disabled. Enable IDENTITY_MODULE_ENABLED "
                "and record explicit authorization/consent before using this module."
            )
        raise IdentityDisabledError(
            "Identification backend is not implemented in this prototype "
            "(no galleries, no external face search)."
        )
