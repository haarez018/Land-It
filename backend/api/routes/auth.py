"""
Auth routes — signup, login, logout, OAuth, and current user.
All auth flows are delegated to Supabase; we just proxy the calls.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from backend.dependencies import supabase_client
from backend.auth_deps import get_current_user

router = APIRouter()


class EmailPasswordRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthRequest(BaseModel):
    provider: str  # "google" | "linkedin_oidc" | "github"
    redirect_to: str = ""


# ── Email / password ──────────────────────────────────────────


@router.post("/signup")
async def signup(body: EmailPasswordRequest):
    try:
        resp = supabase_client.client.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
        if resp.user is None:
            raise HTTPException(400, "Signup failed — check your email format and password length (min 6 chars)")
        return {
            "user_id": str(resp.user.id),
            "email": resp.user.email,
            "access_token": resp.session.access_token if resp.session else None,
            "refresh_token": resp.session.refresh_token if resp.session else None,
            "message": "Signup successful. Check your email to confirm your account.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/login")
async def login(body: EmailPasswordRequest):
    try:
        resp = supabase_client.client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        if resp.user is None or resp.session is None:
            raise HTTPException(401, "Invalid email or password")
        return {
            "user_id": str(resp.user.id),
            "email": resp.user.email,
            "full_name": resp.user.user_metadata.get("full_name"),
            "avatar_url": resp.user.user_metadata.get("avatar_url"),
            "access_token": resp.session.access_token,
            "refresh_token": resp.session.refresh_token,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e))


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    try:
        supabase_client.client.auth.sign_out()
        return {"message": "Logged out"}
    except Exception:
        return {"message": "Logged out"}


# ── OAuth (Google, LinkedIn, GitHub) ─────────────────────────


@router.post("/oauth/url")
async def get_oauth_url(body: OAuthRequest):
    """
    Return the Supabase OAuth redirect URL.
    Frontend redirects the user to this URL; Supabase handles the OAuth dance
    and redirects back to redirect_to with the session tokens in the URL fragment.
    """
    valid_providers = {"google", "linkedin_oidc", "github"}
    if body.provider not in valid_providers:
        raise HTTPException(400, f"Provider must be one of: {sorted(valid_providers)}")
    try:
        resp = supabase_client.client.auth.sign_in_with_oauth({
            "provider": body.provider,
            "options": {"redirect_to": body.redirect_to} if body.redirect_to else {},
        })
        return {"url": resp.url, "provider": body.provider}
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Refresh token ─────────────────────────────────────────────


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    try:
        resp = supabase_client.client.auth.refresh_session(body.refresh_token)
        if resp.session is None:
            raise HTTPException(401, "Invalid refresh token")
        return {
            "access_token": resp.session.access_token,
            "refresh_token": resp.session.refresh_token,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e))


# ── Current user ──────────────────────────────────────────────


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.user_metadata.get("full_name") if user.user_metadata else None,
        "avatar_url": user.user_metadata.get("avatar_url") if user.user_metadata else None,
    }
