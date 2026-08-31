import sqlite3
from pathlib import Path

from watchpost.checker import CheckResult

# columns added after the table already shipped - each gets upgraded into
# an existing history.db in place instead of making people delete their data
_MIGRATED_COLUMNS = [
    ("slow", "INTEGER NOT NULL DEFAULT 0"),
    ("response_body", "TEXT"),
]


def connect(db_path="data/history.db"):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)  # sqlite won't create the folder itself
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checks (
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
    for name, coltype in _MIGRATED_COLUMNS:
        _ensure_column(conn, name, coltype)
    conn.commit()
    return conn


def _ensure_column(conn, name, coltype):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(checks)")}
    if name not in columns:
        conn.execute(f"ALTER TABLE checks ADD COLUMN {name} {coltype}")


def save_result(conn, result):
    conn.execute(
        """
        INSERT INTO checks (endpoint_name, url, timestamp, success, status_code,
                             latency_ms, error, slow, response_body)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.endpoint_name,
            result.url,
            result.timestamp,
            int(result.success),
            result.status_code,
            result.latency_ms,
            result.error,
            int(result.slow),
            result.response_body,
        ),
    )
    conn.commit()


def save_all(conn, results):
    for r in results:
        save_result(conn, r)


def recent_checks(conn, endpoint_name, limit=10):
    rows = conn.execute(
        """
        SELECT endpoint_name, url, success, status_code, latency_ms, timestamp, error, slow, response_body
        FROM checks
        WHERE endpoint_name = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (endpoint_name, limit),
    ).fetchall()

    return [
        CheckResult(
            endpoint_name=row[0],
            url=row[1],
            success=bool(row[2]),
            status_code=row[3],
            latency_ms=row[4],
            timestamp=row[5],
            error=row[6],
            slow=bool(row[7]),
            response_body=row[8],
        )
        for row in rows
    ]
