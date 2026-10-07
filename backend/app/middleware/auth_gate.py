from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.app.services.auth_tokens import COOKIE_NAME, parse_session_token
from backend.app.settings import settings

PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/auth/login",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)


class AuthGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.cpw_auth_enabled:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS:
            return await call_next(request)
        username = parse_session_token(request.cookies.get(COOKIE_NAME))
        if not username:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        request.state.auth_username = username
        return await call_next(request)
