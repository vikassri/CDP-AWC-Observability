from __future__ import annotations

from backend.app.settings import settings


def sync_knox_jwt_file() -> bool:
    """Write JWT to secrets/knox.jwt for Prometheus bearer_token_file (never log token)."""
    token = (settings.knox_jwt or settings.hadoop_jwt or "").strip()
    if not token:
        return False
    settings.cpw_secrets_dir.mkdir(parents=True, exist_ok=True)
    path = settings.cpw_secrets_dir / "knox.jwt"
    path.write_text(token, encoding="utf-8")
    path.chmod(0o600)
    return True
