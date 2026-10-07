from backend.app.services.nifi_overview import _analyze_app_log_lines, _has_federated_metrics


def test_analyze_app_log_bulletin_error_is_flagged() -> None:
    lines = [
        'INFO Bulletin [ERROR] Processor stopped — nifi.bulletin',
        "2024-01-01 INFO normal startup complete",
    ]
    flagged, bulletins = _analyze_app_log_lines(lines)
    assert len(bulletins) == 1
    assert len(flagged) == 1
    assert "Processor stopped" in flagged[0]


def test_analyze_app_log_warning_bulletin_not_flagged_as_error() -> None:
    lines = ["INFO Bulletin [WARNING] Queue full — nifi.bulletin"]
    flagged, bulletins = _analyze_app_log_lines(lines)
    assert len(bulletins) == 1
    assert flagged == []


def test_analyze_app_log_plain_exception() -> None:
    lines = ["ERROR java.lang.NullPointerException in handler"]
    flagged, bulletins = _analyze_app_log_lines(lines)
    assert bulletins == []
    assert len(flagged) == 1


def test_has_federated_metrics_heap() -> None:
    assert _has_federated_metrics({"memory_usage_pct": 42.0}) is True


def test_has_federated_metrics_empty() -> None:
    assert _has_federated_metrics({"exporter_up": 0.0}) is False
