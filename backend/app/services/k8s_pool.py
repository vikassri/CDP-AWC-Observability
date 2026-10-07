from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.api_client import ApiClient


async def _api_for(kubeconfig_path: Path, context: str) -> ApiClient:
    return await config.new_client_from_config(config_file=str(kubeconfig_path), context=context)


async def check_cluster_health(kubeconfig_path: Path, context: str) -> dict[str, str | bool]:
    if not kubeconfig_path.is_file():
        return {"healthy": False, "message": f"kubeconfig missing: {kubeconfig_path}"}
    try:
        api = await _api_for(kubeconfig_path, context)
        try:
            v1 = client.VersionApi(api)
            version = await v1.get_code()
            return {"healthy": True, "message": f"Kubernetes {version.git_version}"}
        finally:
            await api.close()
    except Exception as exc:  # noqa: BLE001
        return {"healthy": False, "message": str(exc)}


async def rollout_restart_namespaced(
    kubeconfig_path: Path,
    context: str,
    namespace: str,
    name: str,
    kind: str,
) -> str:
    api = await _api_for(kubeconfig_path, context)
    try:
        apps = client.AppsV1Api(api)
        restarted = datetime.now(timezone.utc).isoformat()
        body = {"spec": {"template": {"metadata": {"annotations": {"cpw/restartedAt": restarted}}}}}
        if kind.lower() == "statefulset":
            await apps.patch_namespaced_stateful_set(name, namespace, body)
            return f"StatefulSet {namespace}/{name} rollout restart requested"
        await apps.patch_namespaced_deployment(name, namespace, body)
        return f"Deployment {namespace}/{name} rollout restart requested"
    finally:
        await api.close()


async def delete_pod(
    kubeconfig_path: Path,
    context: str,
    namespace: str,
    name: str,
) -> str:
    api = await _api_for(kubeconfig_path, context)
    try:
        core = client.CoreV1Api(api)
        await core.delete_namespaced_pod(name, namespace)
        return f"Pod {namespace}/{name} deleted"
    finally:
        await api.close()
