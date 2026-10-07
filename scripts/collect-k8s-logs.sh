#!/usr/bin/env bash
# Read-only kubectl log harvest: get ns / pods / logs only.
#
# Gotchas:
# - kubectl logs is runtime tail (~10 MiB/stream), not full history; --since=24h can be partial.
# - For retention, query OpenSearch uob-logs-* (Kibana :5601 / Dashboards :5602) via kubectl_logs_to_otel.
# - NiFi: use app-log; the nifi container is nearly empty.
# - Stopped pods: --previous needs --tail=-1 or you only see ~10 crash lines.
#
# Usage:
#   KCDIR=~/Desktop/uob_poc OUT=/tmp/uob-k8s-logs ./scripts/collect-k8s-logs.sh

set -uo pipefail

KCDIR="${KCDIR:-$HOME/Desktop/uob_poc}"
OUT="${OUT:-/tmp/uob-k8s-logs}"
SINCE="${SINCE:-24h}"

mkdir -p "$OUT"

filter_containers() {
  local conts="$1"
  if printf '%s\n' "$conts" | grep -qx 'app-log' && printf '%s\n' "$conts" | grep -qx 'nifi'; then
    printf '%s\n' "$conts" | grep -vx 'nifi'
  else
    printf '%s\n' "$conts"
  fi
}

for kc in "$KCDIR"/*.yaml; do
  [[ -f "$kc" ]] || continue
  cl=$(basename "$kc" .yaml)
  echo "== cluster $cl ($kc) =="
  if ! kubectl --kubeconfig "$kc" cluster-info >/dev/null 2>&1; then
    echo "WARN: unreachable API for $cl — skipping" >&2
    continue
  fi
  for ns in $(kubectl --kubeconfig "$kc" get ns -o jsonpath='{.items[*].metadata.name}'); do
    case "$ns" in kube-*) continue ;; esac
    mkdir -p "$OUT/$cl/$ns"
    for pod in $(kubectl --kubeconfig "$kc" -n "$ns" get pods -o name); do
      p=${pod#pod/}
      conts=$(kubectl --kubeconfig "$kc" -n "$ns" get "$pod" -o jsonpath='{range .spec.initContainers[*]}{.name}{"\n"}{end}{range .spec.containers[*]}{.name}{"\n"}{end}')
      conts=$(filter_containers "$conts")
      for c in $conts; do
        kubectl --kubeconfig "$kc" -n "$ns" logs "$pod" -c "$c" \
          --since="$SINCE" --timestamps > "$OUT/$cl/$ns/${p}_${c}.log" 2>"$OUT/$cl/$ns/${p}_${c}.err" || true
      done
      if [ -n "$(kubectl --kubeconfig "$kc" -n "$ns" get pod "$p" -o jsonpath='{.status.containerStatuses[?(@.restartCount>0)].name}')" ]; then
        for c in $conts; do
          kubectl --kubeconfig "$kc" -n "$ns" logs "$pod" -c "$c" --previous --tail=-1 \
            > "$OUT/$cl/$ns/${p}_${c}.previous.log" 2>/dev/null || true
        done
      fi
    done
  done
done

echo "Done. Output: $OUT"
