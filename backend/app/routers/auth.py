from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.app.services.auth_tokens import (
    COOKIE_NAME,
    issue_session_token,
    parse_session_token,
    verify_credentials,
)
from backend.app.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_MAX_AGE_SEC = 60 * 60 * 12


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AuthUserOut(BaseModel):
    username: str
    authenticated: bool = True


@router.post("/login")
async def login(body: LoginBody, response: Response) -> AuthUserOut:
    if not verify_credentials(body.username.strip(), body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = issue_session_token(settings.cpw_auth_username)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE_SEC,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return AuthUserOut(username=settings.cpw_auth_username)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(request: Request) -> AuthUserOut:
    if not settings.cpw_auth_enabled:
        return AuthUserOut(username=settings.cpw_auth_username)
    username = getattr(request.state, "auth_username", None)
    if not username:
        username = parse_session_token(request.cookies.get(COOKIE_NAME))
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return AuthUserOut(username=username)
