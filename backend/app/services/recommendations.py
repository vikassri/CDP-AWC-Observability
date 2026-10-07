from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from backend.app.settings import settings

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Cloudera CDP on Kubernetes SRE assistant.
Given deployment issues and telemetry, respond with:
1. Likely root cause (2-3 sentences)
2. Recommended actions — only from this allowlist: kubectl rollout restart, delete a single pod, scale deployment, check VPN/kubeconfig, verify Prometheus federation, review NiFi processor state, restart Spark driver, check Trino coordinator logs, Flink job cancel/resubmit, Airflow scheduler/worker restart.
3. Verification steps (metrics or commands to confirm recovery)
Do not suggest arbitrary shell, secrets, or Cloudera Manager changes. Be concise. Use markdown bullets."""


def _compress_context(text: str) -> str:
    try:
        from headroom import compress  # type: ignore[import-not-found]

        return compress(text)
    except Exception:  # noqa: BLE001
        return text[:12_000]


async def recommend_for_issues(payload: dict[str, Any]) -> dict[str, Any]:
    context = {
        "cluster_id": payload.get("cluster_id"),
        "product": payload.get("product"),
        "deployment_name": payload.get("name"),
        "namespace": payload.get("namespace"),
        "status": payload.get("status"),
        "issues": payload.get("issues") or [],
        "metrics": payload.get("metrics") or {},
        "log_flagged": (payload.get("logs") or {}).get("flagged") or [],
        "log_recent": ((payload.get("logs") or {}).get("lines") or [])[:12],
    }
    blob = _compress_context(json.dumps(context, indent=2))

    base = settings.cpw_llm_base_url.rstrip("/")
    if not base:
        return {
            "recommendation": (
                "LLM not configured. Set `CPW_LLM_BASE_URL` (Headroom proxy `http://127.0.0.1:8787/v1`) "
                "and `CPW_LLM_API_KEY` / model in `.env`, then retry."
            ),
            "model": None,
            "source": "static",
        }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.cpw_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.cpw_llm_api_key}"

    body = {
        "model": settings.cpw_llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this deployment context and recommend fixes:\n\n{blob}"},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
    }

    url = f"{base}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {
            "recommendation": content,
            "model": data.get("model") or settings.cpw_llm_model,
            "source": "llm",
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("Recommendation LLM call failed: %s", exc)
        return {
            "recommendation": _fallback_recommendation(context),
            "model": None,
            "source": "rules",
            "error": str(exc),
        }


def _fallback_recommendation(context: dict[str, Any]) -> str:
    issues = context.get("issues") or []
    product = str(context.get("product") or "service")
    lines = ["**Rule-based suggestions** (LLM unavailable)", ""]
    for issue in issues[:5]:
        low = issue.lower()
        if "pod" in low and "not ready" in low:
            lines.append("- Check pod events and consider deleting the stuck pod if CrashLoopBackOff.")
        elif "port-forward" in low or "federation" in low:
            lines.append("- Ensure VPN is up and CAO collectors are running; verify Prometheus target `nifi_federate` is UP.")
        elif "processor" in low and "stopped" in low:
            lines.append("- In NiFi UI, inspect stopped processors; restart affected processor group or rollout NiFi pods.")
        elif "fail" in low:
            lines.append(f"- Inspect {product} application logs and restart the failed workload via rollout restart.")
        elif "log" in low or "error" in low:
            lines.append("- Tail logs for the scanned pod and fix the first root exception; then rollout restart the deployment.")
        else:
            lines.append(f"- Investigate: {issue}")
    if len(lines) <= 2:
        lines.append("- No specific issues listed; verify cluster health and collector telemetry.")
    lines.append("")
    lines.append("- After action, confirm metrics and that deployment status returns to **Healthy** in CAO.")
    return "\n".join(lines)
