"""FastAPI dependency: verify Supabase JWT and return the authenticated user."""

from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.dependencies import supabase_client

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """
    Verify the Bearer token via Supabase auth.get_user().
    Returns the Supabase User object on success.
    Raises HTTP 401 if the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        resp = supabase_client.client.auth.get_user(credentials.credentials)
        if resp.user is None:
            raise ValueError("No user in response")
        return resp.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(user=Depends(get_current_user)) -> str:
    """Convenience dep that returns just the user UUID string."""
    return str(user.id)
