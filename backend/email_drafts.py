import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"
logger = logging.getLogger("aura.email_drafts")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_drafts_db():
    """Ensure the drafts table exists in aura.db."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_address TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                source_email_id TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_drafts_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "to_address": row["to_address"],
        "subject": row["subject"],
        "body": row["body"],
        "source_email_id": row["source_email_id"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def create_draft(
    to_address: str,
    subject: str,
    body: str,
    source_email_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new draft in drafts table with 'draft' status."""
    created_at = datetime.now(timezone.utc).isoformat()
    status = "draft"

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO drafts (to_address, subject, body, source_email_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (to_address.strip(), subject.strip(), body.strip(), source_email_id, status, created_at),
        )
        conn.commit()
        draft_id = cursor.lastrowid

    logger.info(f"Created email draft #{draft_id} to '{to_address}'")
    return get_draft(draft_id)


def get_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single draft by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, to_address, subject, body, source_email_id, status, created_at FROM drafts WHERE id = ?",
            (draft_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def list_drafts() -> List[Dict[str, Any]]:
    """List all drafts, newest first."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, to_address, subject, body, source_email_id, status, created_at FROM drafts ORDER BY id DESC"
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def update_draft(
    draft_id: int,
    to_address: str,
    subject: str,
    body: str,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Update draft contents and optional status."""
    draft = get_draft(draft_id)
    if not draft:
        raise ValueError(f"Draft #{draft_id} not found.")

    new_status = status or draft["status"]
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE drafts
            SET to_address = ?, subject = ?, body = ?, status = ?
            WHERE id = ?
            """,
            (to_address.strip(), subject.strip(), body.strip(), new_status, draft_id),
        )
        conn.commit()

    return get_draft(draft_id)


def set_draft_status(draft_id: int, status: str) -> Dict[str, Any]:
    """Update status of a draft (e.g. 'draft', 'pending approval', 'sent')."""
    draft = get_draft(draft_id)
    if not draft:
        raise ValueError(f"Draft #{draft_id} not found.")

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE drafts SET status = ? WHERE id = ?",
            (status, draft_id),
        )
        conn.commit()

    logger.info(f"Draft #{draft_id} status updated to '{status}'")
    return get_draft(draft_id)


def mark_sent(draft_id: int) -> Dict[str, Any]:
    """Mark a draft as sent."""
    return set_draft_status(draft_id, "sent")
