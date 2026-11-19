import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"
logger = logging.getLogger("aura.reminders")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_reminders_db():
    """Ensure the reminders table exists."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_reminders_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "remind_at": row["remind_at"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def create_reminder(title: str, remind_at: str) -> Dict[str, Any]:
    """Create a new reminder with pending status."""
    created_at = datetime.now(timezone.utc).isoformat()
    status = "pending"

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reminders (title, remind_at, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (title.strip(), remind_at.strip(), status, created_at),
        )
        conn.commit()
        rem_id = cursor.lastrowid

    logger.info(f"Created reminder #{rem_id}: '{title}' at {remind_at}")
    return get_reminder(rem_id)


def get_reminder(rem_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, title, remind_at, status, created_at FROM reminders WHERE id = ?",
            (rem_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def list_reminders() -> List[Dict[str, Any]]:
    """List all reminders, pending first, then by remind_at."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, remind_at, status, created_at FROM reminders
            ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, remind_at ASC
            """
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def list_due() -> List[Dict[str, Any]]:
    """
    List reminders that are due (remind_at <= current time and status == 'pending').
    Compares ISO timestamps flexibly.
    """
    now_iso = datetime.now().isoformat()
    now_utc_iso = datetime.now(timezone.utc).isoformat()

    all_reminders = list_reminders()
    due_list = []

    for r in all_reminders:
        if r["status"] != "pending":
            continue

        remind_str = r["remind_at"]
        try:
            # Try parsing ISO
            r_dt = datetime.fromisoformat(remind_str)
            # Compare based on timezone awareness
            if r_dt.tzinfo is not None:
                current_dt = datetime.now(timezone.utc)
            else:
                current_dt = datetime.now()

            if r_dt <= current_dt:
                due_list.append(r)
        except Exception:
            # String comparison fallback
            if remind_str <= now_iso or remind_str <= now_utc_iso:
                due_list.append(r)

    return due_list


def mark_done(rem_id: int) -> Dict[str, Any]:
    """
    Mark a reminder as done.
    Rule: Only a pending reminder can be marked done.
    """
    r = get_reminder(rem_id)
    if not r:
        raise ValueError(f"Reminder #{rem_id} not found.")

    if r["status"] != "pending":
        raise ValueError(
            f"Reminder #{rem_id} cannot be marked done: current status is '{r['status']}'."
        )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE reminders SET status = 'done' WHERE id = ? AND status = 'pending'",
            (rem_id,),
        )
        conn.commit()

    logger.info(f"Reminder #{rem_id} marked as DONE: {r['title']}")
    return get_reminder(rem_id)
