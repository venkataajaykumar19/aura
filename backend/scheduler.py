import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.approvals import list_pending
from backend.connectors.calendar import list_today_events
from backend.connectors.gmail import list_recent_emails
from backend.memory import get as memory_get
from backend.reminders import list_due

logger = logging.getLogger("aura.scheduler")

# Single global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def build_briefing_text() -> str:
    """
    Build plain-text briefing message.
    Format: date line, then 'Calendar:', 'Gmail:', 'Approvals:', 'Reminders:' lines,
    each with real data or 'none' (or 'not connected' if disconnected).
    No emoji spam.
    """
    now = datetime.now()
    date_line = now.strftime("%A, %d %B %Y")

    # Calendar
    cal = list_today_events()
    if not cal.get("connected"):
        cal_line = "Calendar: not connected"
    else:
        events = cal.get("events", [])
        if not events:
            cal_line = "Calendar: none"
        else:
            ev_summaries = []
            for ev in events:
                t = ev.get("start_time", "")
                title = ev.get("title", "Event")
                ev_summaries.append(f"{title} ({t})" if t else title)
            cal_line = f"Calendar: {', '.join(ev_summaries)}"

    # Gmail
    gmail = list_recent_emails(limit=5)
    if not gmail.get("connected"):
        gmail_line = "Gmail: not connected"
    else:
        emails = gmail.get("emails", [])
        if not emails:
            gmail_line = "Gmail: none"
        else:
            subjects = [e.get("subject", "No subject") for e in emails[:3]]
            subj_str = ", ".join(f"'{s}'" for s in subjects if s)
            gmail_line = f"Gmail: {len(emails)} recent emails ({subj_str})"

    # Approvals
    pending = list_pending()
    if not pending:
        approvals_line = "Approvals: none"
    else:
        approvals_line = f"Approvals: {len(pending)} pending action{'s' if len(pending) != 1 else ''}"

    # Reminders
    due = list_due()
    if not due:
        reminders_line = "Reminders: none"
    else:
        titles = [r.get("title", "") for r in due[:3]]
        reminders_line = f"Reminders: {len(due)} due ({', '.join(titles)})"

    return f"{date_line}\n\n{cal_line}\n{gmail_line}\n{approvals_line}\n{reminders_line}"


async def send_briefing_to_telegram(chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send the daily briefing message to the saved telegram_chat_id.
    If no chat_id is saved or provided, logs and returns cleanly.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not token.strip():
        logger.warning("TELEGRAM_BOT_TOKEN is not set, skipping briefing.")
        return {"sent": False, "reason": "TELEGRAM_BOT_TOKEN is not set in .env."}

    target_chat_id = chat_id or memory_get("telegram_chat_id")
    if not target_chat_id:
        logger.warning("No Telegram chat id saved, skipping briefing")
        return {"sent": False, "reason": "No Telegram chat id saved"}

    message_text = build_briefing_text()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": target_chat_id, "text": message_text},
            )
            data = resp.json()
            if resp.status_code == 200 and data.get("ok"):
                logger.info(f"Morning briefing successfully sent to Telegram chat {target_chat_id}")
                return {"sent": True, "chat_id": target_chat_id, "message": message_text}
            else:
                desc = data.get("description", f"HTTP {resp.status_code}")
                logger.error(f"Failed to send briefing to Telegram: {desc}")
                return {"sent": False, "reason": desc}
    except Exception as e:
        logger.error(f"Exception sending briefing to Telegram: {e}")
        return {"sent": False, "reason": str(e)}


def get_scheduler() -> AsyncIOScheduler:
    """Return the singleton AsyncIOScheduler instance configured with Asia/Kolkata timezone."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        _scheduler.add_job(
            send_briefing_to_telegram,
            trigger="cron",
            hour=8,
            minute=0,
            id="daily_morning_briefing",
            replace_existing=True,
        )
    return _scheduler


def start_scheduler():
    """Start the scheduler, guarded so only one scheduler runs on reloads."""
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("AURA APScheduler started (Asia/Kolkata timezone, daily 08:00 AM job registered)")
    else:
        logger.info("AURA APScheduler is already running.")


def stop_scheduler():
    """Stop the scheduler cleanly on application shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("AURA APScheduler stopped cleanly.")
        _scheduler = None


def get_scheduler_status() -> Dict[str, Any]:
    """Inspect scheduler status and registered jobs."""
    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        nxt = None
        try:
            nxt = job.next_run_time.isoformat() if getattr(job, "next_run_time", None) else None
        except Exception:
            pass
        jobs.append({
            "id": job.id,
            "next_run_time": nxt,
            "trigger": str(job.trigger),
        })
    return {
        "running": sched.running,
        "timezone": str(sched.timezone),
        "jobs": jobs,
    }
