"""Bearer-token -> tenant auth. Tenant is derived from the credential only."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


def resolve_tenant(token_map: Mapping[str, str], token: str | None) -> str | None:
    """Pure lookup: a token maps to a tenant, or None if missing/unknown."""
    if not token:
        return None
    return token_map.get(token)


_bearer = HTTPBearer(auto_error=False)


def get_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    token = credentials.credentials if credentials else None
    tenant_id = resolve_tenant(request.app.state.token_map, token)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing credential",
        )
    return tenant_id
