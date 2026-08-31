import sqlite3

from watchpost.history import connect, recent_checks, save_all, save_result

from helpers import make_result


def test_creates_db_file_and_parent_dir(tmp_path):
    db_path = tmp_path / "nested" / "history.db"
    conn = connect(db_path)
    assert db_path.exists()
    conn.close()


def test_save_and_read_round_trip(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result())

    rows = recent_checks(conn, "api")
    assert len(rows) == 1
    saved = rows[0]
    assert saved.endpoint_name == "api"
    assert saved.status_code == 200
    assert saved.success is True
    assert saved.latency_ms == 100.0
    assert saved.timestamp == 1000.0
    conn.close()


def test_recent_checks_orders_newest_first(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(timestamp=1000.0))
    save_result(conn, make_result(timestamp=3000.0))
    save_result(conn, make_result(timestamp=2000.0))

    rows = recent_checks(conn, "api")
    assert [r.timestamp for r in rows] == [3000.0, 2000.0, 1000.0]
    conn.close()


def test_recent_checks_respects_limit(tmp_path):
    conn = connect(tmp_path / "history.db")
    for i in range(5):
        save_result(conn, make_result(timestamp=float(i)))

    rows = recent_checks(conn, "api", limit=2)
    assert len(rows) == 2
    conn.close()


def test_recent_checks_filters_by_endpoint(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(name="a", timestamp=1.0))
    save_result(conn, make_result(name="b", timestamp=2.0))

    rows = recent_checks(conn, "a")
    assert len(rows) == 1
    assert rows[0].endpoint_name == "a"
    conn.close()


def test_recent_checks_unknown_endpoint_returns_empty(tmp_path):
    conn = connect(tmp_path / "history.db")
    rows = recent_checks(conn, "nothing-here")
    assert rows == []
    conn.close()


def test_save_all_writes_every_result(tmp_path):
    conn = connect(tmp_path / "history.db")
    results = [make_result(name="a", timestamp=1.0), make_result(name="b", timestamp=2.0)]
    save_all(conn, results)

    assert len(recent_checks(conn, "a")) == 1
    assert len(recent_checks(conn, "b")) == 1
    conn.close()


def test_stores_failure_with_error_message(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(success=False, status_code=None, latency_ms=None, error="timed out"))

    saved = recent_checks(conn, "api")[0]
    assert saved.success is False
    assert saved.status_code is None
    assert saved.error == "timed out"
    conn.close()


def test_stores_slow_flag(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(slow=True))

    saved = recent_checks(conn, "api")[0]
    assert saved.slow is True
    conn.close()


def test_stores_response_body(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(success=False, status_code=500, response_body='{"error": "boom"}'))

    saved = recent_checks(conn, "api")[0]
    assert saved.response_body == '{"error": "boom"}'
    conn.close()


def test_upgrades_existing_db_missing_response_body_column(tmp_path):
    # this is the realistic case for anyone upgrading from the previous
    # session - slow already exists, response_body doesn't yet
    db_path = tmp_path / "history.db"

    old_conn = sqlite3.connect(str(db_path))
    old_conn.execute("""
        CREATE TABLE checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_name TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp REAL NOT NULL,
            success INTEGER NOT NULL,
            status_code INTEGER,
            latency_ms REAL,
            error TEXT,
            slow INTEGER NOT NULL DEFAULT 0
        )
    """)
    old_conn.commit()
    old_conn.close()

    conn = connect(db_path)
    save_result(conn, make_result(response_body="test body"))

    rows = recent_checks(conn, "api")
    assert len(rows) == 1
    assert rows[0].response_body == "test body"
    conn.close()


def test_upgrades_existing_db_missing_slow_column(tmp_path):
    db_path = tmp_path / "history.db"

    # simulate a history.db written before the slow column existed
    old_conn = sqlite3.connect(str(db_path))
    old_conn.execute("""
        CREATE TABLE checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint_name TEXT NOT NULL,
            url TEXT NOT NULL,
            timestamp REAL NOT NULL,
            success INTEGER NOT NULL,
            status_code INTEGER,
            latency_ms REAL,
            error TEXT
        )
    """)
    old_conn.commit()
    old_conn.close()

    conn = connect(db_path)  # should upgrade the existing table, not crash
    save_result(conn, make_result())

    rows = recent_checks(conn, "api")
    assert len(rows) == 1
    assert rows[0].slow is False
    conn.close()
