from collectors.knox_sd import _parse_knox_url


def test_parse_knox_full_url() -> None:
    target, path = _parse_knox_url(
        "https://cdf.cdf01.example.com/gateway/cdf/dfx-nifi/metrics/prometheus"
    )
    assert target == "cdf.cdf01.example.com:443"
    assert path == "/gateway/cdf/dfx-nifi/metrics/prometheus"
