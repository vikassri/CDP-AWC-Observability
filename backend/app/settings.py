from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.services.recipients import parse_recipient_csv

REPO_ROOT = Path(__file__).resolve().parents[2]

__all__ = ["Settings", "settings", "REPO_ROOT"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), extra="ignore")

    cpw_config_dir: Path = REPO_ROOT / "config"
    cpw_kubeconfig_dir: Path = REPO_ROOT / "kubeconfigs"
    cpw_secrets_dir: Path = REPO_ROOT / "secrets"
    cpw_file_sd_dir: Path = REPO_ROOT / "deploy/data/prometheus/file_sd"
    cpw_prometheus_url: str = "http://127.0.0.1:9090"
    # Hostname Prometheus uses to scrape hub status exporters (use host.docker.internal when Prom runs in Docker on Mac)
    cpw_scrape_host: str = "127.0.0.1"
    cpw_grafana_url: str = "http://127.0.0.1:3000"
    cpw_otel_logs_endpoint: str = "http://127.0.0.1:4318/v1/logs"
    cpw_opensearch_url: str = "http://127.0.0.1:9200"
    database_url: str = f"sqlite+aiosqlite:///{REPO_ROOT / 'deploy/data/cpw.db'}"
    knox_jwt: str = ""
    hadoop_jwt: str = ""
    collector_interval_sec: int = 60
    alert_eval_interval_sec: int = 15
    cpw_overview_cache_sec: float = 1.25
    cpw_llm_base_url: str = "http://127.0.0.1:8787/v1"
    cpw_llm_model: str = "openai/gpt-4o-mini"
    cpw_llm_api_key: str = ""

    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "alerts@cpw.local"
    smtp_start_tls: bool = False
    smtp_use_tls: bool = False
    alert_default_recipients: str = ""

    cpw_auth_enabled: bool = True
    cpw_auth_username: str = "admin"
    cpw_auth_password: str = "admin"
    cpw_auth_secret: str = "cao-dev-session-secret-change-in-production"


def _normalize_database_url(url: str) -> str:
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix) and not url.startswith(f"sqlite+aiosqlite:////"):
        rel = url[len(prefix) :]
        if rel and not rel.startswith("/"):
            return prefix + str((REPO_ROOT / rel).resolve())
    return url


_settings = Settings()
settings = Settings(
    **_settings.model_dump() | {"database_url": _normalize_database_url(_settings.database_url)}
)


def reload_settings() -> Settings:
    global settings
    fresh = Settings()
    settings = Settings(
        **fresh.model_dump() | {"database_url": _normalize_database_url(fresh.database_url)}
    )
    return settings


def default_alert_recipients() -> list[str]:
    return parse_recipient_csv(settings.alert_default_recipients)
