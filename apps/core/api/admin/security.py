"""Admin API security helpers.

Admin endpoints are sensitive: they can modify runtime configuration and install plugins.

Policy:
- If CERISE_ADMIN_TOKEN is set, require a matching token via either:
  - Authorization: Bearer <token>
  - X-Admin-Token: <token>
- If CERISE_ADMIN_TOKEN is not set, allow admin API access only from localhost.
"""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Request, status

_ENV_ADMIN_TOKEN = "CERISE_ADMIN_TOKEN"


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    token = request.headers.get("x-admin-token")
    if token:
        return token.strip()

    return None


def require_admin(request: Request) -> None:
    """FastAPI dependency enforcing the admin access policy."""

    expected = (os.environ.get(_ENV_ADMIN_TOKEN) or "").strip()
    if expected:
        got = _extract_token(request) or ""
        if not secrets.compare_digest(got, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return

    host = request.client.host if request.client else ""
    if host in {"127.0.0.1", "::1", "localhost"}:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin API is local-only. Set CERISE_ADMIN_TOKEN to enable remote access.",
    )
