from backend.app.services.awc_catalog import build_engine_catalog, fleet_console_url


def test_fleet_console_url() -> None:
    url = fleet_console_url()
    assert "console.awc.spoc.cloudera-labs.com" in url
    assert "engines" in url


def test_engine_catalog_count() -> None:
    catalog = build_engine_catalog()
    assert len(catalog["engines"]) == 7
    assert catalog["source"] == "static_clusters_yaml"
