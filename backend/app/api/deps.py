"""Auth-ready dependency. Disabled unless AUTH_ENABLED=true."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


class Principal:
    def __init__(self, name: str, role: str) -> None:
        self.name = name
        self.role = role


async def get_principal(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not settings.auth_enabled:
        return Principal("anonymous", "operator")
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or missing API key")
    return Principal("operator", "operator")
