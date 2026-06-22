import sqlite3
from contextlib import contextmanager
import config


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                login       TEXT NOT NULL,
                date        TEXT NOT NULL,
                work_start  TEXT,
                work_end    TEXT,
                duration    INTEGER,
                active_time INTEGER,
                bitrix_time INTEGER,
                onec_time   INTEGER,
                browser_time INTEGER,
                achievements TEXT,
                uploaded_at TEXT NOT NULL,
                UNIQUE(login, date)
            );

            CREATE TABLE IF NOT EXISTS known_employees (
                login       TEXT PRIMARY KEY,
                first_seen  TEXT NOT NULL,
                last_seen   TEXT NOT NULL
            );
        """)


@contextmanager
def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_metrics(login: str, date: str, metrics: dict):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO daily_metrics
                (login, date, work_start, work_end, duration, active_time,
                 bitrix_time, onec_time, browser_time, achievements, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(login, date) DO UPDATE SET
                work_start = excluded.work_start,
                work_end = excluded.work_end,
                duration = excluded.duration,
                active_time = excluded.active_time,
                bitrix_time = excluded.bitrix_time,
                onec_time = excluded.onec_time,
                browser_time = excluded.browser_time,
                achievements = excluded.achievements,
                uploaded_at = excluded.uploaded_at
        """, (
            login, date,
            metrics.get("work_start"),
            metrics.get("work_end"),
            metrics.get("duration"),
            metrics.get("active_time"),
            metrics.get("bitrix_time"),
            metrics.get("onec_time"),
            metrics.get("browser_time"),
            metrics.get("achievements"),
        ))


def upsert_employee(login: str, date: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO known_employees (login, first_seen, last_seen)
            VALUES (?, ?, ?)
            ON CONFLICT(login) DO UPDATE SET
                last_seen = MAX(excluded.last_seen, known_employees.last_seen)
        """, (login, date, date))


def get_all_employees():
    with get_db() as conn:
        rows = conn.execute("SELECT login FROM known_employees ORDER BY login").fetchall()
        return [r["login"] for r in rows]


def get_metrics_for_date(date: str):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_metrics WHERE date = ?", (date,)
        ).fetchall()
        return {r["login"]: dict(r) for r in rows}
