import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"
logger = logging.getLogger("aura.notes")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_notes_db():
    """Ensure the notes table exists in aura.db."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_notes_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": row["tags"] or "",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_note(
    title: Optional[str] = "",
    content: str = "",
    tags: Optional[str] = "",
) -> Dict[str, Any]:
    """
    Create a new note in aura.db.
    If no title is provided, uses the first 6 words of the content as the title.
    """
    content_clean = (content or "").strip()
    if not content_clean:
        raise ValueError("Note content cannot be empty.")

    title_clean = (title or "").strip()
    if not title_clean:
        words = content_clean.split()
        title_clean = " ".join(words[:6]) if words else "Untitled Note"

    tags_clean = (tags or "").strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes (title, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title_clean, content_clean, tags_clean, now_iso, now_iso),
        )
        conn.commit()
        note_id = cursor.lastrowid

    logger.info(f"Created note #{note_id}: '{title_clean}'")
    return get_note(note_id)


def get_note(note_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single note by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, title, content, tags, created_at, updated_at FROM notes WHERE id = ?",
            (note_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def list_notes(limit: int = 50) -> List[Dict[str, Any]]:
    """List notes, newest first."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def search_notes(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Case-insensitive search on title and content, newest first.
    """
    q_pattern = f"%{query.strip().lower()}%"
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, title, content, tags, created_at, updated_at
            FROM notes
            WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? OR LOWER(COALESCE(tags, '')) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q_pattern, q_pattern, q_pattern, limit),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def delete_note(note_id: int) -> bool:
    """Delete a note by ID. Returns True if deleted, False if not found."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"Deleted note #{note_id}")
    return deleted
