from backend.app.services.promql_helpers import apply_cluster_label, normalize_promql


def test_apply_cluster_replaces_placeholder() -> None:
    q = 'sum(nifi_amount_flowfiles_queued{cluster="$cluster"})'
    assert apply_cluster_label(q, "cdf") == 'sum(nifi_amount_flowfiles_queued{cluster="cdf"})'


def test_normalize_promql_adds_zero_default_on_plus() -> None:
    q = 'sum(a{cluster="x"}) + sum(b{cluster="x"})'
    out = normalize_promql(q)
    assert "or on() vector(0)" in out
    assert out.count("+") == 1


def test_apply_cluster_repairs_stripped_brace() -> None:
    broken = 'sum(nifi_amount_flowfiles_queuedcluster="cdf")'
    fixed = apply_cluster_label(broken, "cdf")
    assert '{cluster="cdf"}' in fixed or 'cluster="cdf"' in fixed
