from watchpost.cli import cmd_report
from watchpost.history import connect, save_all

from helpers import make_result


class Args:
    """stand-in for argparse.Namespace so tests don't have to go through parse_args"""
    def __init__(self, config, db, window=20):
        self.config = str(config)
        self.db = str(db)
        self.window = window


def test_cmd_report_prints_status_and_incidents(tmp_path, capsys):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("""
endpoints:
  - name: api
    url: https://example.com
""")
    db_path = tmp_path / "history.db"
    conn = connect(db_path)
    save_all(conn, [
        make_result(name="api", timestamp=1.0, success=True),
        make_result(name="api", timestamp=2.0, success=False, status_code=500),
    ])
    conn.close()

    exit_code = cmd_report(Args(config_path, db_path))
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "api" in out
    assert "uptime" in out


def test_cmd_report_friendly_error_on_missing_config(tmp_path, capsys):
    exit_code = cmd_report(Args(tmp_path / "nope.yaml", tmp_path / "history.db"))
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "not found" in err
