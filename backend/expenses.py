import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "aura.db"
logger = logging.getLogger("aura.expenses")

VALID_CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Other"]


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_expenses_db():
    """Ensure the expenses table exists in aura.db."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT,
                spent_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


init_expenses_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "amount": float(row["amount"]),
        "category": row["category"],
        "note": row["note"] or "",
        "spent_at": row["spent_at"],
        "created_at": row["created_at"],
    }


def normalize_category(category: Optional[str]) -> str:
    """Normalize category to one of Food, Travel, Shopping, Bills, Other."""
    if not category:
        return "Other"
    cat_lower = category.strip().lower()
    mapping = {
        "food": "Food",
        "dining": "Food",
        "lunch": "Food",
        "dinner": "Food",
        "breakfast": "Food",
        "groceries": "Food",
        "coffee": "Food",
        "tea": "Food",
        "travel": "Travel",
        "transport": "Travel",
        "transit": "Travel",
        "cab": "Travel",
        "taxi": "Travel",
        "uber": "Travel",
        "ola": "Travel",
        "auto": "Travel",
        "petrol": "Travel",
        "diesel": "Travel",
        "fuel": "Travel",
        "flight": "Travel",
        "shopping": "Shopping",
        "clothes": "Shopping",
        "ecommerce": "Shopping",
        "amazon": "Shopping",
        "flipkart": "Shopping",
        "bills": "Bills",
        "bill": "Bills",
        "utility": "Bills",
        "electricity": "Bills",
        "wifi": "Bills",
        "recharge": "Bills",
        "rent": "Bills",
    }
    return mapping.get(cat_lower, "Other" if cat_lower not in [c.lower() for c in VALID_CATEGORIES] else category.capitalize())


def add_expense(
    amount: float,
    category: str,
    note: Optional[str] = "",
    spent_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Log a new expense in aura.db.
    Default spent_at is current local timestamp.
    """
    amount_val = float(amount)
    category_norm = normalize_category(category)
    now_local = datetime.now()
    spent_at_val = spent_at.strip() if spent_at and spent_at.strip() else now_local.strftime("%Y-%m-%d %H:%M:%S")
    created_at_val = datetime.now(timezone.utc).isoformat()
    note_val = (note or "").strip()

    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (amount, category, note, spent_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (amount_val, category_norm, note_val, spent_at_val, created_at_val),
        )
        conn.commit()
        expense_id = cursor.lastrowid

    logger.info(f"Logged expense #{expense_id}: ₹{amount_val} for {category_norm} ({note_val})")
    return get_expense(expense_id)


def get_expense(expense_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single expense by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT id, amount, category, note, spent_at, created_at FROM expenses WHERE id = ?",
            (expense_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None


def list_expenses(limit: int = 50) -> List[Dict[str, Any]]:
    """List expenses, newest first (by spent_at descending, then id descending)."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT id, amount, category, note, spent_at, created_at
            FROM expenses
            ORDER BY spent_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def total_for_month(year: int, month: int) -> float:
    """Calculate total expenses for a given month and year."""
    prefix = f"{year:04d}-{month:02d}%"
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT COALESCE(SUM(amount), 0.0) as total FROM expenses WHERE spent_at LIKE ?",
            (prefix,),
        )
        row = cursor.fetchone()
        return round(float(row["total"]), 2) if row else 0.0


def total_for_today() -> float:
    """Calculate total expenses logged for today."""
    today_str = datetime.now().strftime("%Y-%m-%d") + "%"
    with get_db_connection() as conn:
        cursor = conn.execute(
            "SELECT COALESCE(SUM(amount), 0.0) as total FROM expenses WHERE spent_at LIKE ?",
            (today_str,),
        )
        row = cursor.fetchone()
        return round(float(row["total"]), 2) if row else 0.0


def expenses_summary() -> Dict[str, Any]:
    """
    Return summary:
    - month_total: total spent in the current month
    - today_total: total spent today
    - by_category: breakdown by category for the current month
    """
    now = datetime.now()
    month_tot = total_for_month(now.year, now.month)
    today_tot = total_for_today()

    prefix = f"{now.year:04d}-{now.month:02d}%"
    by_cat: Dict[str, float] = {}
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0.0) as cat_total
            FROM expenses
            WHERE spent_at LIKE ?
            GROUP BY category
            """,
            (prefix,),
        )
        for row in cursor.fetchall():
            by_cat[row["category"]] = round(float(row["cat_total"]), 2)

    return {
        "month_total": month_tot,
        "this_month_total": month_tot,
        "today_total": today_tot,
        "by_category": by_cat,
    }


def delete_expense(expense_id: int) -> bool:
    """Delete an expense by ID. Returns True if deleted, False if not found."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info(f"Deleted expense #{expense_id}")
    return deleted
