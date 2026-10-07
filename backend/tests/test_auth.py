from __future__ import annotations

from backend.app.services.auth_tokens import (
    issue_session_token,
    parse_session_token,
    verify_credentials,
)


def test_verify_credentials_admin_default() -> None:
    assert verify_credentials("admin", "admin") is True
    assert verify_credentials("admin", "wrong") is False
    assert verify_credentials("other", "admin") is False


def test_session_token_round_trip() -> None:
    token = issue_session_token("admin")
    assert parse_session_token(token) == "admin"
    assert parse_session_token("admin.tampered") is None
    assert parse_session_token(None) is None
