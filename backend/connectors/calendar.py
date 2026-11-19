import json
import logging
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build

from backend.approvals import get_action
from backend.connectors.gmail import get_credentials

logger = logging.getLogger("aura.calendar")


def get_status() -> Dict[str, Any]:
    """Check whether Google Calendar is connected."""
    creds = get_credentials()
    if creds and (creds.valid or creds.refresh_token):
        return {"connected": True}
    return {"connected": False}


def list_today_events() -> Dict[str, Any]:
    """
    List today's events (title, start time, end time).
    If Google is not connected, return {"connected": false} instead of crashing.
    """
    creds = get_credentials()
    if not creds:
        return {"connected": False, "events": []}

    try:
        service = build("calendar", "v3", credentials=creds)

        # Get local start and end of day
        now = datetime.now()
        start_of_day = datetime.combine(now.date(), time.min).astimezone().isoformat()
        end_of_day = datetime.combine(now.date(), time.max).astimezone().isoformat()

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        items = events_result.get("items", [])
        events = []
        for item in items:
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            title = item.get("summary", "(No Title)")
            events.append(
                {
                    "id": item.get("id"),
                    "title": title,
                    "start_time": start,
                    "end_time": end,
                }
            )

        return {"connected": True, "events": events}
    except Exception as e:
        logger.error(f"Error fetching Calendar events: {e}")
        return {"connected": False, "error": str(e), "events": []}


def execute_create_event(approval_id: int) -> Dict[str, Any]:
    """
    Execute event creation on Google Calendar.
    ONLY runs after an approval entry exists for it and is marked 'approved'.
    """
    action = get_action(approval_id)
    if not action:
        raise ValueError(f"Approval action #{approval_id} does not exist.")

    if action["status"] != "approved":
        raise PermissionError(
            f"Action #{approval_id} has status '{action['status']}'. Human approval is required before creating events."
        )

    creds = get_credentials()
    if not creds:
        return {"connected": False, "error": "Google Calendar is not connected."}

    payload = action.get("payload")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}

    title = payload.get("title", "Meeting")
    date_str = payload.get("date")
    time_str = payload.get("time")

    # Format ISO datetime
    try:
        if date_str and time_str:
            dt_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        else:
            dt_start = datetime.now()
    except Exception:
        dt_start = datetime.now()

    # Default duration: 30 minutes
    duration_min = payload.get("duration_minutes", 30)
    from datetime import timedelta
    dt_end = dt_start + timedelta(minutes=duration_min)

    event_body = {
        "summary": title,
        "description": f"Created via AURA (Approval #{approval_id})",
        "start": {"dateTime": dt_start.astimezone().isoformat()},
        "end": {"dateTime": dt_end.astimezone().isoformat()},
    }

    try:
        service = build("calendar", "v3", credentials=creds)
        created_event = (
            service.events()
            .insert(calendarId="primary", body=event_body)
            .execute()
        )
        logger.info(f"Calendar event created: {created_event.get('htmlLink')}")
        return {
            "connected": True,
            "created": True,
            "event_id": created_event.get("id"),
            "link": created_event.get("htmlLink"),
        }
    except Exception as e:
        logger.error(f"Failed to create Calendar event: {e}")
        return {"connected": True, "created": False, "error": str(e)}
