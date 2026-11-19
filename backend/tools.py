"""
Tools for AURA's Gemini AI brain.
Reuses existing connectors and approval engine. Never executes sensitive actions directly.
"""

import logging
from typing import Any, Dict

from backend.approvals import create_action
from backend.connectors.calendar import list_today_events as cal_list_today
from backend.connectors.gmail import list_recent_emails as gmail_list_recent
from backend.expenses import add_expense, total_for_today
from backend.memory import get_facts as mem_get_facts, save_fact as mem_save_fact
from backend.notes import create_note as db_create_note, search_notes as db_search_notes

logger = logging.getLogger("aura.tools")


def get_today_events() -> Dict[str, Any]:
    """Get the user's scheduled calendar events for today from Google Calendar.

    Returns:
        dict: A dictionary containing:
            - connected (bool): False if Google Calendar is not connected.
            - events (list): List of events today with title, start_time, and end_time.
    """
    logger.info("Tool called: get_today_events")
    try:
        res = cal_list_today()
        if not res.get("connected"):
            return {"connected": False, "events": [], "message": "Google Calendar is not connected."}
        return res
    except Exception as e:
        logger.error(f"Error in get_today_events: {e}")
        return {"connected": False, "events": [], "error": str(e)}


def get_recent_emails() -> Dict[str, Any]:
    """Get the most recent 5 emails from the user's Gmail inbox.

    Returns:
        dict: A dictionary containing:
            - connected (bool): False if Gmail is not connected.
            - emails (list): List of recent emails with sender, subject, snippet, and time.
    """
    logger.info("Tool called: get_recent_emails")
    try:
        res = gmail_list_recent(limit=5)
        if not res.get("connected"):
            return {"connected": False, "emails": [], "message": "Gmail is not connected."}
        return res
    except Exception as e:
        logger.error(f"Error in get_recent_emails: {e}")
        return {"connected": False, "emails": [], "error": str(e)}


def request_calendar_event(title: str, date: str, time: str, duration_minutes: int = 30) -> Dict[str, Any]:
    """Request to schedule a meeting or event on Google Calendar.
    Does NOT create the event immediately; creates a pending action requiring user approval.

    Args:
        title: Title or subject of the meeting/event (e.g. 'Team Standup' or 'Test').
        date: Date in YYYY-MM-DD format (e.g. '2026-11-20').
        time: Start time in HH:MM 24-hour format (e.g. '15:00').
        duration_minutes: Duration in minutes (default is 30).

    Returns:
        dict: A dictionary confirming that a pending approval was created.
    """
    logger.info(f"Tool called: request_calendar_event({title}, {date}, {time}, {duration_minutes})")
    summary = f"Schedule meeting: '{title}' on {date} at {time}"
    payload = {
        "title": title,
        "date": date,
        "time": time,
        "duration_minutes": duration_minutes or 30,
    }
    action = create_action(
        action_type="CREATE_CALENDAR_EVENT",
        summary=summary,
        payload=payload,
    )
    return {
        "status": "pending_approval",
        "action_id": action["id"],
        "summary": summary,
        "message": f"I've created a pending request to schedule '{title}' on {date} at {time}. Please approve it in your AURA dashboard or Telegram.",
    }


def request_send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Request to send an email via Gmail.
    Does NOT send the email immediately; creates a pending action requiring user approval.

    Args:
        to: Recipient email address.
        subject: Subject line of the email.
        body: Plain text content of the email.

    Returns:
        dict: A dictionary confirming that a pending approval was created.
    """
    logger.info(f"Tool called: request_send_email({to}, {subject})")
    summary = f"Send email to {to}: '{subject}'"
    payload = {
        "to": to,
        "subject": subject,
        "body": body,
    }
    action = create_action(
        action_type="SEND_EMAIL",
        summary=summary,
        payload=payload,
    )
    return {
        "status": "pending_approval",
        "action_id": action["id"],
        "summary": summary,
        "message": f"I've drafted the email to {to} with subject '{subject}'. Please approve sending it in your AURA dashboard or Telegram.",
    }


def get_facts() -> Dict[str, str]:
    """Retrieve all known facts about the user from long-term memory."""
    return mem_get_facts()


def save_fact(key: str, value: str) -> Dict[str, Any]:
    """Save or update a learned fact about the user in long-term memory."""
    return mem_save_fact(key, value)


def log_expense(amount: float, category: str, note: str = "") -> Dict[str, Any]:
    """Log an expense paid by the user. Call this whenever the user mentions spending or paying money.
    Does NOT need approval because logging an expense is not a sensitive external action.

    Args:
        amount: The numeric amount spent (e.g. 200, 500, 150.50).
        category: The category of expense ('Food', 'Travel', 'Shopping', 'Bills', or 'Other').
        note: Short description of the expense (e.g. 'lunch', 'petrol', 'coffee').

    Returns:
        dict: A dictionary containing the saved expense and the total amount spent today.
    """
    logger.info(f"Tool called: log_expense(amount={amount}, category={category}, note={note})")
    saved = add_expense(amount=amount, category=category, note=note)
    today_total = total_for_today()
    return {
        "status": "logged",
        "expense": saved,
        "total_spent_today": today_total,
        "message": f"Logged ₹{float(amount):.0f} for {saved['category']} ({note}). Total spent today: ₹{today_total:.0f}.",
    }


def save_note(title: str = "", content: str = "") -> Dict[str, Any]:
    """Save a personal note for the user. Call this when the user says 'note that ...', 'remember this note ...', or 'save a note ...'.
    Does NOT need approval because notes are stored locally.

    Args:
        title: Title of the note. If omitted or empty, the first 6 words of content are used as the title.
        content: The text content of the note.

    Returns:
        dict: A dictionary confirming that the note was saved.
    """
    logger.info(f"Tool called: save_note(title='{title}', content='{content[:40]}...')")
    note = db_create_note(title=title, content=content)
    return {
        "status": "saved",
        "note": note,
        "message": f"Saved note: '{note['title']}'.",
    }


def search_notes(query: str = "") -> Dict[str, Any]:
    """Search the user's personal notes by title or content. Call this when the user asks 'what did I note about ...?', 'find my notes on ...', or 'show my notes'.
    Does NOT need approval because notes are stored locally.

    Args:
        query: Search keywords or phrase (e.g. 'hackathon', 'ideas', 'recipes').

    Returns:
        dict: A dictionary containing the list of matching notes.
    """
    logger.info(f"Tool called: search_notes(query='{query}')")
    matches = db_search_notes(query)
    formatted = [
        {
            "id": m["id"],
            "title": m["title"],
            "content": m["content"],
            "date": m["created_at"],
        }
        for m in matches
    ]
    return {
        "query": query,
        "count": len(formatted),
        "notes": formatted,
    }

