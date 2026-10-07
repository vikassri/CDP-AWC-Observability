from __future__ import annotations

import hmac
import secrets
from hashlib import sha256

from backend.app.settings import settings

COOKIE_NAME = "cao_session"


def verify_credentials(username: str, password: str) -> bool:
    if not username or not password:
        return False
    user_ok = secrets.compare_digest(username, settings.cpw_auth_username)
    pass_ok = secrets.compare_digest(password, settings.cpw_auth_password)
    return user_ok and pass_ok


def issue_session_token(username: str) -> str:
    payload = username.strip()
    digest = hmac.new(
        settings.cpw_auth_secret.encode("utf-8"),
        payload.encode("utf-8"),
        sha256,
    ).hexdigest()
    return f"{payload}.{digest}"


def parse_session_token(token: str | None) -> str | None:
    if not token or "." not in token:
        return None
    username, _, sig = token.partition(".")
    if not username or not sig:
        return None
    expected = issue_session_token(username)
    if not secrets.compare_digest(token, expected):
        return None
    if username != settings.cpw_auth_username:
        return None
    return username
