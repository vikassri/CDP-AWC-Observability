from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

from backend.app.config_loader import load_awc, load_clusters
from backend.app.services.awc_catalog import fleet_console_url
from backend.app.services.env_file import write_env_updates
from backend.app.settings import REPO_ROOT, Settings, reload_settings, settings
from backend.app.services.knox_secrets import sync_knox_jwt_file
from collectors.knox_sd import sync_knox_targets

ENV_PATH = REPO_ROOT / ".env"
AWC_PATH = settings.cpw_config_dir / "awc.yaml"

_FIELD_TO_ENV: dict[str, str] = {
    "cpw_llm_base_url": "CPW_LLM_BASE_URL",
    "cpw_llm_model": "CPW_LLM_MODEL",
    "cpw_llm_api_key": "CPW_LLM_API_KEY",
    "cpw_overview_cache_sec": "CPW_OVERVIEW_CACHE_SEC",
    "cpw_prometheus_url": "CPW_PROMETHEUS_URL",
    "cpw_scrape_host": "CPW_SCRAPE_HOST",
    "cpw_grafana_url": "CPW_GRAFANA_URL",
    "cpw_otel_logs_endpoint": "CPW_OTEL_LOGS_ENDPOINT",
    "cpw_opensearch_url": "CPW_OPENSEARCH_URL",
    "knox_jwt": "KNOX_JWT",
    "hadoop_jwt": "HADOOP_JWT",
    "collector_interval_sec": "COLLECTOR_INTERVAL_SEC",
    "alert_eval_interval_sec": "ALERT_EVAL_INTERVAL_SEC",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_user": "SMTP_USER",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_from": "SMTP_FROM",
    "smtp_start_tls": "SMTP_START_TLS",
    "smtp_use_tls": "SMTP_USE_TLS",
    "alert_default_recipients": "ALERT_DEFAULT_RECIPIENTS",
}


def _secret_configured(value: str) -> bool:
    return bool((value or "").strip())


def _mask_secret(value: str) -> str:
    if not _secret_configured(value):
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}…{value[-2:]}"


def build_settings_snapshot() -> dict[str, Any]:
    awc = load_awc()
    jwt_path = settings.cpw_secrets_dir / "knox.jwt"
    has_jwt_file = jwt_path.is_file() and jwt_path.stat().st_size > 0
    knox_targets = sync_knox_targets()

    return {
        "env_file": str(ENV_PATH),
        "inference": {
            "base_url": settings.cpw_llm_base_url,
            "model": settings.cpw_llm_model,
            "api_key_configured": _secret_configured(settings.cpw_llm_api_key),
            "api_key_hint": _mask_secret(settings.cpw_llm_api_key),
            "overview_cache_sec": settings.cpw_overview_cache_sec,
            "gateway_example": "https://your-omniroute-host/v1",
            "notes": [
                "Point CPW_LLM_BASE_URL at your OmniRoute (or other OpenAI-compatible) gateway.",
                "For HTTPS with a private CA, set SSL_CERT_FILE when starting the backend (see README).",
                "Recommendations API: POST /recommendations",
            ],
        },
        "cloudera": {
            "console_base_url": awc.console_base_url,
            "engines_path": awc.engines_path,
            "fleet_console_url": fleet_console_url(awc),
            "registered_engines": len(load_clusters()),
            "knox_jwt_configured": has_jwt_file or _secret_configured(settings.knox_jwt),
            "hadoop_jwt_configured": _secret_configured(settings.hadoop_jwt),
            "knox_bearer_token_file": str(jwt_path),
            "knox_scrape_targets": len(knox_targets),
            "knox_note": "Optional HTTPS NiFi metrics via Knox; federation remains primary.",
        },
        "telemetry": {
            "prometheus_url": settings.cpw_prometheus_url,
            "scrape_host": settings.cpw_scrape_host,
            "grafana_url": settings.cpw_grafana_url,
            "otel_logs_endpoint": settings.cpw_otel_logs_endpoint,
            "opensearch_url": settings.cpw_opensearch_url,
            "collector_interval_sec": settings.collector_interval_sec,
            "file_sd_dir": str(settings.cpw_file_sd_dir),
        },
        "alerts": {
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_from": settings.smtp_from,
            "smtp_user_configured": _secret_configured(settings.smtp_user),
            "smtp_password_configured": _secret_configured(settings.smtp_password),
            "smtp_start_tls": settings.smtp_start_tls,
            "smtp_use_tls": settings.smtp_use_tls,
            "default_recipients": settings.alert_default_recipients,
            "eval_interval_sec": settings.alert_eval_interval_sec,
        },
        "paths": {
            "config_dir": str(settings.cpw_config_dir),
            "kubeconfig_dir": str(settings.cpw_kubeconfig_dir),
            "secrets_dir": str(settings.cpw_secrets_dir),
        },
    }


def apply_settings_patch(payload: dict[str, Any]) -> dict[str, Any]:
    env_updates: dict[str, str | None] = {}
    awc_updates: dict[str, str] = {}

    inference = payload.get("inference") or {}
    if isinstance(inference, dict):
        for field in ("base_url", "model", "overview_cache_sec"):
            if field in inference and inference[field] is not None:
                key = {
                    "base_url": "cpw_llm_base_url",
                    "model": "cpw_llm_model",
                    "overview_cache_sec": "cpw_overview_cache_sec",
                }[field]
                env_updates[_FIELD_TO_ENV[key]] = str(inference[field])
        if inference.get("api_key") is not None:
            raw = str(inference["api_key"]).strip()
            if raw and not raw.startswith("**") and "…" not in raw:
                env_updates["CPW_LLM_API_KEY"] = raw

    cloudera = payload.get("cloudera") or {}
    if isinstance(cloudera, dict):
        if cloudera.get("console_base_url"):
            awc_updates["console_base_url"] = str(cloudera["console_base_url"]).strip()
        if cloudera.get("engines_path"):
            awc_updates["engines_path"] = str(cloudera["engines_path"]).strip()
        if cloudera.get("knox_jwt") is not None:
            raw = str(cloudera["knox_jwt"]).strip()
            if raw:
                env_updates["KNOX_JWT"] = raw
        if cloudera.get("hadoop_jwt") is not None:
            raw = str(cloudera["hadoop_jwt"]).strip()
            if raw:
                env_updates["HADOOP_JWT"] = raw

    telemetry = payload.get("telemetry") or {}
    if isinstance(telemetry, dict):
        mapping = {
            "prometheus_url": "cpw_prometheus_url",
            "scrape_host": "cpw_scrape_host",
            "grafana_url": "cpw_grafana_url",
            "otel_logs_endpoint": "cpw_otel_logs_endpoint",
            "opensearch_url": "cpw_opensearch_url",
            "collector_interval_sec": "collector_interval_sec",
        }
        for ui_key, setting_key in mapping.items():
            if ui_key in telemetry and telemetry[ui_key] is not None:
                env_updates[_FIELD_TO_ENV[setting_key]] = str(telemetry[ui_key])

    alerts = payload.get("alerts") or {}
    if isinstance(alerts, dict):
        for ui_key, setting_key in {
            "smtp_host": "smtp_host",
            "smtp_port": "smtp_port",
            "smtp_from": "smtp_from",
            "smtp_start_tls": "smtp_start_tls",
            "smtp_use_tls": "smtp_use_tls",
            "default_recipients": "alert_default_recipients",
            "eval_interval_sec": "alert_eval_interval_sec",
        }.items():
            if ui_key in alerts and alerts[ui_key] is not None:
                env_updates[_FIELD_TO_ENV[setting_key]] = str(alerts[ui_key])
        if alerts.get("smtp_user") is not None:
            raw = str(alerts["smtp_user"]).strip()
            if raw:
                env_updates["SMTP_USER"] = raw
        if alerts.get("smtp_password") is not None:
            raw = str(alerts["smtp_password"]).strip()
            if raw:
                env_updates["SMTP_PASSWORD"] = raw

    if env_updates:
        write_env_updates(ENV_PATH, env_updates)
        reload_settings()
        sync_knox_jwt_file()
        sync_knox_targets()

    if awc_updates and AWC_PATH.is_file():
        raw_yaml = yaml.safe_load(AWC_PATH.read_text(encoding="utf-8")) or {}
        raw_yaml.update(awc_updates)
        AWC_PATH.write_text(
            yaml.safe_dump(raw_yaml, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )

    return build_settings_snapshot()


async def probe_inference(settings_obj: Settings | None = None) -> dict[str, Any]:
    cfg = settings_obj or settings
    base = (cfg.cpw_llm_base_url or "").rstrip("/")
    if not base:
        return {"ok": False, "message": "CPW_LLM_BASE_URL is not set"}

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if cfg.cpw_llm_api_key:
        headers["Authorization"] = f"Bearer {cfg.cpw_llm_api_key}"

    body = {
        "model": cfg.cpw_llm_model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: CPW inference OK"},
        ],
        "max_tokens": 16,
        "temperature": 0,
    }
    url = f"{base}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        snippet = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {
            "ok": True,
            "message": "Inference endpoint reachable",
            "model": data.get("model") or cfg.cpw_llm_model,
            "sample": str(snippet).strip()[:120],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": str(exc)}
