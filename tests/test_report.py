from watchpost.config import Endpoint
from watchpost.history import connect, save_all
from watchpost.report import build_report, endpoint_report, format_report

from helpers import make_result


def test_no_data_yet(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="fresh", url="https://example.com")

    r = endpoint_report(conn, endpoint)
    assert r["status"] == "NO DATA"
    assert r["incidents"] == []
    conn.close()


def test_all_successful_checks(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="api", url="https://example.com")
    save_all(conn, [
        make_result(name="api", timestamp=1.0),
        make_result(name="api", timestamp=2.0),
        make_result(name="api", timestamp=3.0),
    ])

    r = endpoint_report(conn, endpoint)
    assert r["status"] == "UP"
    assert r["uptime_pct"] == 100.0
    assert r["incidents"] == []
    conn.close()


def test_uptime_percentage_with_mixed_results(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="api", url="https://example.com")
    save_all(conn, [
        make_result(name="api", timestamp=1.0, success=True),
        make_result(name="api", timestamp=2.0, success=False, status_code=500),
        make_result(name="api", timestamp=3.0, success=True),
        make_result(name="api", timestamp=4.0, success=True),
    ])

    r = endpoint_report(conn, endpoint)
    assert r["uptime_pct"] == 75.0
    assert len(r["incidents"]) == 1
    assert r["incidents"][0].status_code == 500
    conn.close()


def test_status_reflects_latest_check_not_the_average(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="api", url="https://example.com")
    save_all(conn, [
        make_result(name="api", timestamp=1.0, success=True),
        make_result(name="api", timestamp=2.0, success=True),
        make_result(name="api", timestamp=3.0, success=False, status_code=500),  # most recent
    ])

    r = endpoint_report(conn, endpoint)
    assert r["status"] == "DOWN"  # even though 2 of the last 3 checks were fine
    assert r["uptime_pct"] == round(100 * 2 / 3, 1)
    conn.close()


def test_window_limits_how_far_back_uptime_looks(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="api", url="https://example.com")
    # one old failure that should fall outside a 5-check window, everything since is fine
    save_all(conn, [make_result(name="api", timestamp=0.0, success=False, status_code=500)])
    save_all(conn, [make_result(name="api", timestamp=float(i)) for i in range(1, 6)])

    r = endpoint_report(conn, endpoint, window=5)
    assert r["uptime_pct"] == 100.0
    conn.close()


def test_build_report_covers_every_configured_endpoint_even_with_no_history(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoints = [
        Endpoint(name="a", url="https://example.com/a"),
        Endpoint(name="b", url="https://example.com/b"),
    ]
    save_all(conn, [make_result(name="a", timestamp=1.0)])  # "b" never checked yet

    reports = build_report(conn, endpoints)
    assert [r["name"] for r in reports] == ["a", "b"]
    assert reports[1]["status"] == "NO DATA"
    conn.close()


def test_format_report_includes_uptime_and_incidents(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="flaky", url="https://example.com")
    save_all(conn, [
        make_result(name="flaky", timestamp=1.0, success=True),
        make_result(name="flaky", timestamp=2.0, success=False, status_code=503),
    ])

    text = format_report(build_report(conn, [endpoint]))
    assert "flaky" in text
    assert "uptime" in text
    assert "recent incidents" in text
    assert "503" in text
    conn.close()


def test_format_report_handles_connection_failure_with_no_status_code(tmp_path):
    conn = connect(tmp_path / "history.db")
    endpoint = Endpoint(name="down", url="https://example.com")
    save_all(conn, [
        make_result(name="down", timestamp=1.0, success=False, status_code=None,
                    latency_ms=None, error="connection failed"),
    ])

    text = format_report(build_report(conn, [endpoint]))
    assert "down" in text
    assert "connection failed" in text
    conn.close()
