import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"
logger = logging.getLogger("aura.memory")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db():
    """Ensure preferences and facts tables exist."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_memory_db()


# -----------------------------------------------------------------------------
# Preferences (Existing table and functions)
# -----------------------------------------------------------------------------
def get(key: str) -> Optional[str]:
    """Retrieve a value by key from preferences."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_val(key: str, value: str):
    """Store or update a key/value pair in preferences."""
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO preferences (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value)
        )
        conn.commit()


def get_all() -> Dict[str, str]:
    """Retrieve all saved preferences as a dictionary."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT key, value FROM preferences")
        return {row["key"]: row["value"] for row in cursor.fetchall()}


# -----------------------------------------------------------------------------
# Long-Term Memory: Facts
# -----------------------------------------------------------------------------
def save_fact(key: str, value: str) -> Dict[str, Any]:
    """Save or update a learned fact in long-term memory."""
    clean_key = key.strip().lower()
    clean_val = value.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO facts (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (clean_key, clean_val, now_iso)
        )
        conn.commit()

    logger.info(f"Saved fact: '{clean_key}' -> '{clean_val}'")
    return {"key": clean_key, "value": clean_val, "updated_at": now_iso}


def get_facts() -> Dict[str, str]:
    """Retrieve all facts as a key-value dictionary."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT key, value FROM facts ORDER BY key ASC")
        return {row["key"]: row["value"] for row in cursor.fetchall()}


def list_facts() -> List[Dict[str, str]]:
    """Retrieve all facts as a list with updated_at metadata for the UI."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT key, value, updated_at FROM facts ORDER BY updated_at DESC")
        return [
            {"key": row["key"], "value": row["value"], "updated_at": row["updated_at"]}
            for row in cursor.fetchall()
        ]


def delete_fact(key: str) -> bool:
    """Delete a fact from long-term memory."""
    clean_key = key.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM facts WHERE key = ?", (clean_key,))
        conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"Deleted fact: '{clean_key}'")
    return deleted
