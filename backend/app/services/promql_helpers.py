from __future__ import annotations

import re


def with_zero_default(promql: str) -> str:
    """Prometheus binary ops drop results when one side is empty; treat as 0."""
    inner = promql.strip()
    if inner.startswith("(") and inner.endswith(")"):
        return f"({inner} or on() vector(0))"
    return f"({inner} or on() vector(0))"


def normalize_promql(promql: str) -> str:
    if " + " not in promql:
        return promql
    parts = [p.strip() for p in promql.split("+")]
    return " + ".join(with_zero_default(part) for part in parts)


def apply_cluster_label(promql: str, cluster: str | None) -> str:
    if not cluster:
        return promql
    out = promql.replace("$cluster", cluster)
    # Some proxies strip `{` `}` from query strings — repair common breakage.
    out = re.sub(
        r"([a-zA-Z_:][a-zA-Z0-9_:]*)(cluster=)",
        r"\1{\2",
        out,
    )
    if "cluster=" not in out and "{" not in out:
        out = f'{out}{{cluster="{cluster}"}}'
    return out
