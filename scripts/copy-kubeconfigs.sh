#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${KUBECONFIG_SRC:-$HOME/Desktop/uob_poc}"
DEST_DIR="${REPO_ROOT}/kubeconfigs"

declare -a PAIRS=(
  "cdf:cdf_kubeconfig.yaml"
  "cde:cde_kubeconfig.yaml"
  "csa:csa_kubeconfig.yaml"
  "cle:cle_kubeconfig.yaml"
  "cwo:cwo_kubeconfig.yaml"
  "cai:cai_kubeconfig.yaml"
  "polaris:polaris_kubeconfig.yaml"
)

mkdir -p "$DEST_DIR"
for entry in "${PAIRS[@]}"; do
  id="${entry%%:*}"
  file="${entry#*:}"
  src="${SRC_DIR}/${file}"
  dest="${DEST_DIR}/${id}.yaml"
  if [[ ! -f "$src" ]]; then
    echo "Missing: $src" >&2
    exit 1
  fi
  cp "$src" "$dest"
  chmod 600 "$dest"
  echo "Copied $file -> kubeconfigs/${id}.yaml"
done

echo "Done. kubeconfigs/ is gitignored."
