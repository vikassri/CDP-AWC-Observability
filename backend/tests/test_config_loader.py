from backend.app.config_loader import load_awc, load_clusters


def test_load_clusters_count() -> None:
    clusters = load_clusters()
    assert len(clusters) == 7
    assert {c.id for c in clusters} == {"cdf", "cde", "csa", "cle", "cwo", "cai", "polaris"}


def test_load_awc_url() -> None:
    awc = load_awc()
    assert "console.awc.spoc.cloudera-labs.com" in awc.console_base_url
