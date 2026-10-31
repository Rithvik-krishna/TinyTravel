"""SQLite database module for TinyTravel.
Manages searches, offers, event stream replay log, and historical price records.
"""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Optional, Union, Any

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_DB_PATH = Path(__file__).parent / "tinytravel.db"


def get_conn(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Return a thread-safe connection to the SQLite database."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> None:
    """Initialize database schema with required tables."""
    conn = get_conn(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id TEXT PRIMARY KEY,
                request TEXT NOT NULL,
                status TEXT NOT NULL,
                results TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id TEXT PRIMARY KEY,
                search_id TEXT NOT NULL,
                body TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT NOT NULL,
                t_ms INTEGER NOT NULL,
                event TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hotel TEXT NOT NULL,
                platform TEXT NOT NULL,
                amount REAL NOT NULL,
                captured_at TEXT NOT NULL,
                offer_id TEXT
            )
        """)
    conn.close()


def save_search(
    search_id: str,
    request: Union[dict, str],
    status: str = "running",
    results: Optional[Union[dict, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Save or replace a search record."""
    req_json = json.dumps(request) if isinstance(request, dict) else request
    res_json = json.dumps(results) if isinstance(results, dict) else results
    now_iso = datetime.now(IST).isoformat()
    conn = get_conn(db_path)
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO searches (id, request, status, results, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (search_id, req_json, status, res_json, now_iso),
        )
    conn.close()


def update_search(
    search_id: str,
    status: Optional[str] = None,
    results: Optional[Union[dict, str]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Update status and/or results of an existing search."""
    conn = get_conn(db_path)
    with conn:
        if status is not None and results is not None:
            res_json = json.dumps(results) if isinstance(results, dict) else results
            conn.execute(
                "UPDATE searches SET status = ?, results = ? WHERE id = ?",
                (status, res_json, search_id),
            )
        elif status is not None:
            conn.execute("UPDATE searches SET status = ? WHERE id = ?", (status, search_id))
        elif results is not None:
            res_json = json.dumps(results) if isinstance(results, dict) else results
            conn.execute("UPDATE searches SET results = ? WHERE id = ?", (res_json, search_id))
    conn.close()


def get_search(search_id: str, db_path: Optional[Union[str, Path]] = None) -> Optional[dict]:
    """Retrieve search record by id."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, request, status, results, created_at FROM searches WHERE id = ?", (search_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "request": json.loads(row["request"]),
        "status": row["status"],
        "results": json.loads(row["results"]) if row["results"] else None,
        "created_at": row["created_at"],
    }


def save_offer(
    offer_id: str,
    search_id: str,
    body: Union[dict, str],
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Save an offer record."""
    body_json = json.dumps(body) if isinstance(body, dict) else body
    conn = get_conn(db_path)
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO offers (id, search_id, body) VALUES (?, ?, ?)",
            (offer_id, search_id, body_json),
        )
    conn.close()


def get_offers(search_id: str, db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Get all offers associated with a search."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, search_id, body FROM offers WHERE search_id = ?", (search_id,))
    rows = cur.fetchall()
    conn.close()
    return [json.loads(r["body"]) for r in rows]


def append_event(
    search_id: str,
    t_ms: int,
    event: str,
    data: Union[dict, str],
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Append an event to the immutable event log for replay to late subscribers."""
    data_json = json.dumps(data) if isinstance(data, dict) else data
    now_iso = datetime.now(IST).isoformat()
    conn = get_conn(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO events (search_id, t_ms, event, data, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (search_id, t_ms, event, data_json, now_iso),
        )
    conn.close()


def get_events(search_id: str, db_path: Optional[Union[str, Path]] = None) -> list[dict]:
    """Retrieve all logged events in order for late subscriber replay."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT t_ms, event, data FROM events WHERE search_id = ? ORDER BY id ASC",
        (search_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "t_ms": r["t_ms"],
            "event": r["event"],
            "data": json.loads(r["data"]),
        }
        for r in rows
    ]


def save_price_history(
    hotel: str,
    platform: str,
    amount: float,
    captured_at: str,
    offer_id: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> None:
    """Record a verified final payable price in historical ledger."""
    conn = get_conn(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO price_history (hotel, platform, amount, captured_at, offer_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (hotel, platform, amount, captured_at, offer_id),
        )
    conn.close()


def get_price_history(
    hotel: Optional[str] = None,
    platform: Optional[str] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> list[dict]:
    """Query historical price records."""
    conn = get_conn(db_path)
    cur = conn.cursor()
    query = "SELECT id, hotel, platform, amount, captured_at, offer_id FROM price_history WHERE 1=1"
    params: list[Any] = []
    if hotel:
        query += " AND hotel = ?"
        params.append(hotel)
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    query += " ORDER BY id DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Ensure tables exist on load
init_db()
