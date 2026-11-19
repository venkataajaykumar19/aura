import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"

logger = logging.getLogger("aura.approvals")
logging.basicConfig(level=logging.INFO)


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_approvals_db():
    """Ensure the pending_actions table exists."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_approvals_db()


def create_action(action_type: str, summary: str, payload: Any = None) -> Dict[str, Any]:
    """Create a new pending action requiring explicit approval."""
    payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload or "{}")
    created_at = datetime.now(timezone.utc).isoformat()
    status = "pending"

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO pending_actions (action_type, summary, payload, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action_type, summary, payload_str, status, created_at)
        )
        conn.commit()
        action_id = cursor.lastrowid

    logger.info(f"Created pending action #{action_id} [{action_type}]: {summary}")
    return get_action(action_id)


def get_action(action_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an action by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, action_type, summary, payload, status, created_at FROM pending_actions WHERE id = ?",
            (action_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "action_type": row["action_type"],
            "summary": row["summary"],
            "payload": row["payload"],
            "status": row["status"],
            "created_at": row["created_at"],
        }


def list_pending() -> List[Dict[str, Any]]:
    """List all actions currently in 'pending' status."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, action_type, summary, payload, status, created_at FROM pending_actions WHERE status = 'pending' ORDER BY id DESC"
        )
        return [
            {
                "id": row["id"],
                "action_type": row["action_type"],
                "summary": row["summary"],
                "payload": row["payload"],
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]


def approve(action_id: int) -> Dict[str, Any]:
    """
    Approve a pending action.
    Rule: Only a pending action can be approved. Approving is one-shot.
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action #{action_id} not found.")

    if action["status"] != "pending":
        raise ValueError(
            f"Action #{action_id} cannot be approved: already marked as '{action['status']}'."
        )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE pending_actions SET status = 'approved' WHERE id = ? AND status = 'pending'",
            (action_id,)
        )
        conn.commit()

    logger.info(f"Action #{action_id} APPROVED: {action['summary']}")
    return get_action(action_id)


def reject(action_id: int) -> Dict[str, Any]:
    """
    Reject a pending action.
    Rule: Only a pending action can be rejected.
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action #{action_id} not found.")

    if action["status"] != "pending":
        raise ValueError(
            f"Action #{action_id} cannot be rejected: already marked as '{action['status']}'."
        )

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE pending_actions SET status = 'rejected' WHERE id = ? AND status = 'pending'",
            (action_id,)
        )
        conn.commit()

    logger.info(f"Action #{action_id} REJECTED: {action['summary']}")
    return get_action(action_id)
