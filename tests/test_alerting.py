from watchpost.alerting import detect_transition
from watchpost.history import connect, save_result

from helpers import make_result


def test_first_ever_check_that_fails_reports_down(tmp_path):
    conn = connect(tmp_path / "history.db")
    result = make_result(success=False, status_code=500)
    save_result(conn, result)

    assert detect_transition(conn, result) == "down"
    conn.close()


def test_first_ever_check_that_succeeds_reports_nothing(tmp_path):
    # nobody needs a ping just because the very first check happened to be fine
    conn = connect(tmp_path / "history.db")
    result = make_result(success=True)
    save_result(conn, result)

    assert detect_transition(conn, result) is None
    conn.close()


def test_going_from_up_to_down_reports_down(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(timestamp=1.0, success=True))
    current = make_result(timestamp=2.0, success=False, status_code=500)
    save_result(conn, current)

    assert detect_transition(conn, current) == "down"
    conn.close()


def test_going_from_down_to_up_reports_up(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(timestamp=1.0, success=False, status_code=500))
    current = make_result(timestamp=2.0, success=True)
    save_result(conn, current)

    assert detect_transition(conn, current) == "up"
    conn.close()


def test_staying_down_reports_nothing(tmp_path):
    # this is the whole point - don't alert on every check while it's still broken
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(timestamp=1.0, success=False, status_code=500))
    current = make_result(timestamp=2.0, success=False, status_code=500)
    save_result(conn, current)

    assert detect_transition(conn, current) is None
    conn.close()


def test_staying_up_reports_nothing(tmp_path):
    conn = connect(tmp_path / "history.db")
    save_result(conn, make_result(timestamp=1.0, success=True))
    current = make_result(timestamp=2.0, success=True)
    save_result(conn, current)

    assert detect_transition(conn, current) is None
    conn.close()
