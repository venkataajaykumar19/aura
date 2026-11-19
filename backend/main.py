import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.auth import (
    is_auth_enabled,
    verify_password,
    create_session_token,
    add_session,
    is_valid_session,
    revoke_session,
)

from backend.brain import ask, is_configured, MissingApiKeyError
from backend.memory import (
    get as memory_get,
    set_val as memory_set,
    get_all as memory_get_all,
    save_fact,
    list_facts,
    delete_fact,
)
from backend.approvals import (
    create_action,
    list_pending,
    approve as approvals_approve,
    reject as approvals_reject,
    get_action,
)
from backend.connectors.gmail import (
    get_status as gmail_status,
    get_auth_url as gmail_auth_url,
    handle_oauth_callback,
    list_recent_emails,
    summarise_emails,
    send_email,
    draft_reply,
)
from backend.email_drafts import (
    create_draft,
    get_draft,
    list_drafts,
    update_draft,
    set_draft_status,
    mark_sent,
)
from backend.expenses import (
    add_expense,
    get_expense,
    list_expenses,
    total_for_month,
    expenses_summary,
    delete_expense,
)
from backend.notes import (
    create_note,
    get_note,
    list_notes,
    search_notes,
    delete_note,
)
from backend.connectors.calendar import (
    get_status as calendar_status,
    list_today_events,
    execute_create_event,
)
from backend.reminders import (
    create_reminder,
    list_reminders,
    list_due,
    mark_done as reminder_mark_done,
)
from backend.scheduler import (
    start_scheduler,
    stop_scheduler,
    send_briefing_to_telegram,
    get_scheduler_status,
)

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler guarded against multiple instances
    start_scheduler()
    yield
    # Stop scheduler cleanly on shutdown
    stop_scheduler()


app = FastAPI(title="AURA", lifespan=lifespan)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not is_auth_enabled():
        return await call_next(request)

    path = request.url.path

    # Public paths that never require login:
    if path == "/api/health":
        return await call_next(request)

    if path in ("/api/login", "/login", "/api/auth/status"):
        return await call_next(request)

    if path in ("/style.css", "/favicon.ico") or path.startswith("/static/"):
        return await call_next(request)

    if path == "/api/oauth/callback":
        return await call_next(request)

    # Check session cookie
    token = request.cookies.get("aura_session")
    if is_valid_session(token):
        return await call_next(request)

    # Unauthenticated handling
    if path.startswith("/api/"):
        return JSONResponse(status_code=401, content={"error": "Unauthorized. Please log in."})

    return RedirectResponse(url="/login", status_code=303)


# Pydantic Schemas
class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []


class MemoryItem(BaseModel):
    key: str
    value: str


class ActionCreateRequest(BaseModel):
    action_type: str
    summary: str
    payload: Optional[Any] = None


class CalendarCreateRequest(BaseModel):
    title: str
    date: str
    time: str
    duration_minutes: Optional[int] = 30


class ReminderCreateRequest(BaseModel):
    title: str
    remind_at: str


class DraftCreateRequest(BaseModel):
    to_address: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    source_email_id: Optional[str] = None
    sender: Optional[str] = None
    snippet: Optional[str] = None
    instruction: Optional[str] = None


class DraftUpdateRequest(BaseModel):
    to_address: str
    subject: str
    body: str


class ExpenseCreateRequest(BaseModel):
    amount: float
    category: str
    note: Optional[str] = ""
    spent_at: Optional[str] = None


class NoteCreateRequest(BaseModel):
    title: Optional[str] = ""
    content: str
    tags: Optional[str] = ""


class LoginRequest(BaseModel):
    password: str


# -----------------------------------------------------------------------------
# Authentication Endpoints (Phase 18)
# -----------------------------------------------------------------------------
@app.get("/login")
async def login_page_route():
    login_path = Path(__file__).resolve().parent.parent / "frontend" / "login.html"
    if login_path.exists():
        return FileResponse(str(login_path))
    return HTMLResponse("<h1>AURA Login</h1>")


@app.post("/api/login")
async def login_route(req: LoginRequest):
    if verify_password(req.password):
        token = create_session_token()
        add_session(token)
        res = JSONResponse(content={"ok": True})
        res.set_cookie(
            key="aura_session",
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=86400 * 30,
        )
        return res
    return JSONResponse(status_code=401, content={"error": "Wrong password"})


@app.post("/api/logout")
async def logout_route(request: Request):
    token = request.cookies.get("aura_session")
    revoke_session(token)
    res = JSONResponse(content={"ok": True})
    res.delete_cookie(key="aura_session", path="/")
    return res


@app.get("/api/auth/status")
async def auth_status_route(request: Request):
    token = request.cookies.get("aura_session")
    enabled = is_auth_enabled()
    return {
        "auth_enabled": enabled,
        "logged_in": is_valid_session(token) if enabled else False,
    }


# -----------------------------------------------------------------------------
# System & Brain Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AURA v1"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api/brain/status")
async def brain_status():
    return {"configured": is_configured()}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages = list(request.history)
    messages.append({"role": "user", "content": request.message})
    try:
        reply = ask(messages)
        return {"reply": reply}
    except MissingApiKeyError as e:
        return JSONResponse(
            status_code=503,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to generate response: {str(e)}"}
        )


# -----------------------------------------------------------------------------
# Memory Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/memory")
async def get_memory(key: Optional[str] = None):
    if key:
        val = memory_get(key)
        return {"key": key, "value": val}
    return {"preferences": memory_get_all()}


@app.post("/api/memory")
async def set_memory(item: MemoryItem):
    memory_set(item.key, item.value)
    return {"status": "ok", "key": item.key, "value": item.value}


@app.get("/api/facts")
async def get_facts_route():
    return {"facts": list_facts()}


@app.post("/api/facts")
async def post_fact_route(item: MemoryItem):
    fact = save_fact(item.key, item.value)
    return {"status": "ok", "fact": fact}


@app.delete("/api/facts/{key}")
async def delete_fact_route(key: str):
    deleted = delete_fact(key)
    return {"status": "ok", "deleted": deleted, "key": key}


# -----------------------------------------------------------------------------
# Approvals Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/approvals")
async def get_approvals():
    return list_pending()


@app.post("/api/approvals")
async def create_pending_approval(request: ActionCreateRequest):
    action = create_action(request.action_type, request.summary, request.payload)
    return action


@app.post("/api/approvals/{action_id}/approve")
async def approve_action(action_id: int):
    try:
        action = get_action(action_id)
        if not action:
            return JSONResponse(status_code=404, content={"error": f"Action #{action_id} not found."})

        updated = approvals_approve(action_id)

        execution_result = None
        action_type = updated.get("action_type")
        payload = updated.get("payload")
        if isinstance(payload, str):
            try:
                import json
                payload = json.loads(payload)
            except Exception:
                payload = {}

        if action_type == "CREATE_CALENDAR_EVENT":
            cal_status = calendar_status()
            if cal_status.get("connected"):
                execution_result = execute_create_event(action_id)

        elif action_type == "SEND_EMAIL":
            to_addr = payload.get("to") or payload.get("to_address")
            subj = payload.get("subject", "")
            body_txt = payload.get("body", "")
            draft_id = payload.get("draft_id")

            if to_addr and subj and body_txt:
                execution_result = send_email(action_id, to_addr, subj, body_txt)
                if draft_id:
                    try:
                        mark_sent(int(draft_id))
                    except Exception as err:
                        print(f"Could not mark draft #{draft_id} as sent: {err}")

        return {
            "status": "approved",
            "action": updated,
            "execution": execution_result,
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


@app.post("/api/approvals/{action_id}/reject")
async def reject_action(action_id: int):
    try:
        updated = approvals_reject(action_id)
        return updated
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


# -----------------------------------------------------------------------------
# Gmail Connector Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/gmail/status")
async def get_gmail_status():
    return gmail_status()


@app.get("/api/gmail/auth-url")
async def get_gmail_auth_url():
    return gmail_auth_url()


@app.get("/api/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    if error:
        return HTMLResponse(
            f"<h3>Authentication error</h3><p>{error}</p><a href='/'>Return to AURA</a>"
        )
    if not code:
        return HTMLResponse(
            "<h3>Missing authorization code</h3><a href='/'>Return to AURA</a>"
        )

    try:
        handle_oauth_callback(code, state)
        return HTMLResponse(
            """
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>AURA Connected</title>
              <style>
                body { background: #0F0E0B; color: #F2EFE6; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                .box { border: 1px solid #2A2822; padding: 24px; border-radius: 10px; background: #171613; text-align: center; }
                a { color: #E3B341; text-decoration: none; }
              </style>
            </head>
            <body>
              <div class="box">
                <p>Google account connected successfully.</p>
                <p><a href="/">Return to AURA Dashboard</a></p>
                <script>setTimeout(() => { window.location.href = '/'; }, 1200);</script>
              </div>
            </body>
            </html>
            """
        )
    except Exception as e:
        return HTMLResponse(
            f"<h3>Authentication failed</h3><p>{str(e)}</p><a href='/'>Return to AURA</a>"
        )


@app.get("/api/gmail/recent")
async def get_recent_emails(limit: int = 10):
    return list_recent_emails(limit=limit)


@app.post("/api/gmail/summarise")
async def post_summarise_emails():
    return summarise_emails()


@app.post("/api/gmail/draft")
async def create_email_draft_route(req: DraftCreateRequest):
    """
    Creates a draft in the drafts table and returns it.
    Can use draft_reply(source_email, instruction) or direct fields.
    """
    to_addr = req.to_address or req.sender or ""
    subj = req.subject or ""
    body_txt = req.body or ""
    source_id = req.source_email_id

    if req.instruction and (req.sender or req.source_email_id or req.snippet or req.subject):
        source_email = {
            "sender": req.sender or to_addr,
            "subject": req.subject or "",
            "snippet": req.snippet or "",
            "id": source_id,
        }
        draft_info = draft_reply(source_email, req.instruction)
        to_addr = draft_info.get("to") or to_addr
        subj = draft_info.get("subject") or subj
        body_txt = draft_info.get("body") or body_txt
        source_id = draft_info.get("source_email_id") or source_id

    if not to_addr:
        return JSONResponse(status_code=400, content={"error": "Recipient email (to_address) is required."})

    draft = create_draft(to_address=to_addr, subject=subj, body=body_txt, source_email_id=source_id)
    return draft


@app.get("/api/gmail/drafts")
async def get_email_drafts_route():
    """List drafts, newest first."""
    return list_drafts()


@app.put("/api/gmail/drafts/{draft_id}")
async def update_email_draft_route(draft_id: int, req: DraftUpdateRequest):
    """Update editable draft fields."""
    try:
        updated = update_draft(draft_id, req.to_address, req.subject, req.body)
        return updated
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@app.post("/api/gmail/drafts/{draft_id}/send-for-approval")
async def send_draft_for_approval_route(draft_id: int):
    """
    Creates a pending action via approvals.py with action_type SEND_EMAIL
    and payload containing draft id, to, subject, body — does NOT send.
    """
    draft = get_draft(draft_id)
    if not draft:
        return JSONResponse(status_code=404, content={"error": f"Draft #{draft_id} not found."})

    updated_draft = set_draft_status(draft_id, "pending approval")

    summary = f"Send email to {draft['to_address']}: '{draft['subject']}'"
    payload = {
        "draft_id": draft["id"],
        "to": draft["to_address"],
        "subject": draft["subject"],
        "body": draft["body"],
    }
    action = create_action(
        action_type="SEND_EMAIL",
        summary=summary,
        payload=payload,
    )
    return {
        "status": "pending_approval",
        "action": action,
        "draft": updated_draft,
    }


# -----------------------------------------------------------------------------
# Google Calendar Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/calendar/status")
async def get_calendar_status():
    return calendar_status()


@app.get("/api/calendar/today")
async def get_calendar_today():
    return list_today_events()


@app.post("/api/calendar/create")
async def create_calendar_event_route(request: CalendarCreateRequest):
    summary = f"Schedule meeting: '{request.title}' on {request.date} at {request.time}"
    payload = {
        "title": request.title,
        "date": request.date,
        "time": request.time,
        "duration_minutes": request.duration_minutes or 30,
    }
    action = create_action(
        action_type="CREATE_CALENDAR_EVENT",
        summary=summary,
        payload=payload,
    )
    return {
        "status": "pending_approval",
        "action": action,
    }


# -----------------------------------------------------------------------------
# Reminders & Daily Briefing Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/reminders")
async def get_reminders_route():
    return list_reminders()


@app.post("/api/reminders")
async def post_reminder_route(request: ReminderCreateRequest):
    return create_reminder(request.title, request.remind_at)


@app.post("/api/reminders/{reminder_id}/done")
async def post_reminder_done_route(reminder_id: int):
    try:
        updated = reminder_mark_done(reminder_id)
        return updated
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/api/reminders/due")
async def get_reminders_due_route():
    return list_due()


# -----------------------------------------------------------------------------
# Expenses Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/expenses")
async def get_expenses_route():
    """List expenses, newest first."""
    return list_expenses(limit=50)


@app.post("/api/expenses")
async def create_expense_route(req: ExpenseCreateRequest):
    """Log an expense."""
    if req.amount <= 0:
        return JSONResponse(status_code=400, content={"error": "Amount must be greater than zero."})
    if not req.category or not req.category.strip():
        return JSONResponse(status_code=400, content={"error": "Category is required."})

    exp = add_expense(
        amount=req.amount,
        category=req.category,
        note=req.note or "",
        spent_at=req.spent_at,
    )
    return exp


@app.get("/api/expenses/summary")
async def get_expenses_summary_route():
    """Returns this month total, today total, and total by category."""
    return expenses_summary()


@app.delete("/api/expenses/{expense_id}")
async def delete_expense_route(expense_id: int):
    """Delete an expense by ID."""
    deleted = delete_expense(expense_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": f"Expense #{expense_id} not found."})
    return {"deleted": True, "id": expense_id}


# -----------------------------------------------------------------------------
# Notes Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/notes")
async def get_notes_route(q: Optional[str] = None):
    """Search notes if q is given, otherwise list newest."""
    if q and q.strip():
        return search_notes(q.strip(), limit=50)
    return list_notes(limit=50)


@app.post("/api/notes")
async def create_note_route(req: NoteCreateRequest):
    """Create a new note."""
    if not req.content or not req.content.strip():
        return JSONResponse(status_code=400, content={"error": "Note content cannot be empty."})
    note = create_note(title=req.title, content=req.content, tags=req.tags)
    return note


@app.delete("/api/notes/{note_id}")
async def delete_note_route(note_id: int):
    """Delete a note by ID."""
    deleted = delete_note(note_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": f"Note #{note_id} not found."})
    return {"deleted": True, "id": note_id}


@app.get("/api/briefing")
async def get_briefing_route():
    # 1. Today date
    now = datetime.now()
    today_date_str = now.strftime("%A, %d %B %Y")

    # 2. Calendar events
    cal_data = list_today_events()

    # 3. Gmail recent
    gmail_data = list_recent_emails(limit=5)
    gmail_summary_part: Dict[str, Any] = {"connected": False}
    if gmail_data.get("connected"):
        emails = gmail_data.get("emails", [])
        gmail_summary_part = {
            "connected": True,
            "count": len(emails),
            "subjects": [e.get("subject") for e in emails[:5]],
        }

    # 4. Pending approvals
    pending = list_pending()

    # 5. Due reminders
    due = list_due()

    # 6. Expenses month total
    exp_month_total = total_for_month(now.year, now.month)

    return {
        "date": today_date_str,
        "calendar": cal_data,
        "gmail": gmail_summary_part,
        "pending_approvals_count": len(pending),
        "due_reminders": due,
        "due_reminders_count": len(due),
        "expenses_month_total": exp_month_total,
    }


@app.post("/api/briefing/send-test")
async def send_briefing_test_route():
    """Build the briefing and send it to Telegram now for testing."""
    result = await send_briefing_to_telegram()
    return result


@app.get("/api/scheduler/status")
async def get_scheduler_status_route():
    """Inspect scheduler state and registered jobs."""
    return get_scheduler_status()


# Serve frontend directory as static files at root
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
