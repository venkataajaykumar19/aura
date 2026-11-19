import base64
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from backend.approvals import get_action

logger = logging.getLogger("aura.gmail")
load_dotenv()

def get_redirect_uri() -> str:
    """Resolve OAuth callback URL. Uses RENDER_EXTERNAL_URL on Render, BASE_URL if set, or defaults to localhost."""
    base = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BASE_URL") or "http://localhost:8000"
    return f"{base.rstrip('/')}/api/oauth/callback"


REDIRECT_URI = get_redirect_uri()
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]

DB_PATH = Path(__file__).resolve().parent.parent.parent / "aura.db"


def _init_token_db():
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                service TEXT PRIMARY KEY,
                token_data TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_pending (
                state TEXT PRIMARY KEY,
                code_verifier TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


_init_token_db()


def _save_tokens(service: str, creds_dict: dict):
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO oauth_tokens (service, token_data) VALUES (?, ?)
            ON CONFLICT(service) DO UPDATE SET token_data = excluded.token_data
            """,
            (service, json.dumps(creds_dict)),
        )
        conn.commit()


def _load_tokens(service: str) -> Optional[dict]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.execute(
            "SELECT token_data FROM oauth_tokens WHERE service = ?", (service,)
        )
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                return None
    return None


def get_client_config() -> Optional[dict]:
    load_dotenv(override=True)
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [get_redirect_uri(), "http://localhost:8000/api/oauth/callback"],
        }
    }


def get_credentials() -> Optional[Credentials]:
    tokens = _load_tokens("google")
    if not tokens:
        return None
    try:
        creds = Credentials.from_authorized_user_info(tokens, SCOPES)
        return creds
    except Exception as e:
        logger.warning(f"Failed to load Google credentials: {e}")
        return None


def get_status() -> Dict[str, Any]:
    """Check whether Google / Gmail is connected."""
    creds = get_credentials()
    if creds and (creds.valid or creds.refresh_token):
        return {"connected": True}
    return {"connected": False}


def get_auth_url() -> Dict[str, Any]:
    """Generate the OAuth consent URL and store PKCE code_verifier."""
    config = get_client_config()
    if not config:
        return {
            "connected": False,
            "error": "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET is not set in .env",
            "auth_url": None,
        }

    flow = Flow.from_client_config(config, scopes=SCOPES)
    flow.redirect_uri = get_redirect_uri()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    # Persist PKCE code_verifier for this state
    if flow.code_verifier and state:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                """
                INSERT INTO oauth_pending (state, code_verifier, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(state) DO UPDATE SET code_verifier = excluded.code_verifier
                """,
                (state, flow.code_verifier, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    return {"connected": False, "auth_url": authorization_url}


def handle_oauth_callback(code: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Exchange authorization code for tokens, restoring PKCE code_verifier."""
    config = get_client_config()
    if not config:
        return {"connected": False, "error": "Google credentials missing."}

    code_verifier = None
    if state:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cursor = conn.execute(
                "SELECT code_verifier FROM oauth_pending WHERE state = ?", (state,)
            )
            row = cursor.fetchone()
            if row:
                code_verifier = row[0]

    flow = Flow.from_client_config(config, scopes=SCOPES)
    flow.redirect_uri = get_redirect_uri()
    if code_verifier:
        flow.code_verifier = code_verifier

    flow.fetch_token(code=code)
    creds = flow.credentials

    creds_dict = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    _save_tokens("google", creds_dict)

    # Clean up pending state
    if state:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute("DELETE FROM oauth_pending WHERE state = ?", (state,))
            conn.commit()

    return {"connected": True, "status": "authenticated"}


def list_recent_emails(limit: int = 10) -> Dict[str, Any]:
    """
    List the 10 most recent emails (sender, subject, short snippet).
    If Google is not connected, returns {"connected": false} instead of crashing.
    """
    creds = get_credentials()
    if not creds:
        return {"connected": False, "emails": []}

    try:
        service = build("gmail", "v1", credentials=creds)
        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=limit)
            .execute()
        )
        messages = results.get("messages", [])

        email_items = []
        for msg_summary in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_summary["id"], format="metadata")
                .execute()
            )
            headers = msg.get("payload", {}).get("headers", [])
            sender = next(
                (h["value"] for h in headers if h["name"].lower() == "from"),
                "Unknown Sender",
            )
            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "(No Subject)",
            )
            snippet = msg.get("snippet", "")
            internal_date = msg.get("internalDate", "")

            email_items.append(
                {
                    "id": msg["id"],
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "time": internal_date,
                }
            )

        return {"connected": True, "emails": email_items}
    except Exception as e:
        logger.error(f"Error fetching Gmail messages: {e}")
        return {"connected": False, "error": str(e), "emails": []}


def summarise_emails(emails: Optional[List[dict]] = None) -> Dict[str, Any]:
    """
    Summarise a list of emails using backend/brain.py.
    If Google is not connected, returns {"connected": false} instead of crashing.
    """
    if emails is None:
        recent = list_recent_emails(limit=10)
        if not recent.get("connected"):
            return {"connected": False, "summary": "Gmail is not connected."}
        emails = recent.get("emails", [])

    if not emails:
        return {
            "connected": True,
            "summary": "No emails found in the last 24 hours to summarise.",
        }

    email_digest = "\n---\n".join(
        [
            f"From: {e.get('sender')}\nSubject: {e.get('subject')}\nSnippet: {e.get('snippet')}"
            for e in emails
        ]
    )

    prompt = (
        f"Please provide a calm, concise 2-3 sentence executive summary of these recent emails:\n\n"
        f"{email_digest}"
    )

    try:
        from backend.brain import ask
        summary_text = ask([{"role": "user", "content": prompt}])
        return {"connected": True, "summary": summary_text}
    except Exception as e:
        return {"connected": True, "summary": f"Could not generate summary: {str(e)}"}


def send_email(approval_id: int, to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send an email. ONLY runs after an approval entry exists for it.
    If Google is not connected, returns {"connected": false} instead of crashing.
    """
    action = get_action(approval_id)
    if not action:
        raise ValueError(f"Approval action #{approval_id} does not exist.")

    if action["status"] != "approved":
        raise PermissionError(
            f"Action #{approval_id} has status '{action['status']}'. Sensitive actions require explicit human approval."
        )

    creds = get_credentials()
    if not creds:
        return {"connected": False, "error": "Gmail is not connected."}

    try:
        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        sent_msg = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
        logger.info(f"Email sent successfully. Message ID: {sent_msg.get('id')}")
        return {"connected": True, "sent": True, "message_id": sent_msg.get("id")}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"connected": True, "sent": False, "error": str(e)}


def draft_reply(source_email: Dict[str, Any], instruction: str) -> Dict[str, Any]:
    """
    Takes one recent email (sender, subject, snippet/body) and a short instruction.
    Uses brain.ask() to write a short, polite draft reply in the same language as the original email,
    with a proper subject (Re: ...).
    Returns draft dictionary with to, subject, body, and source_email_id.
    Does NOT send anything.
    """
    raw_sender = source_email.get("sender", "")
    match = re.search(r"<([^>]+)>", raw_sender)
    to_address = match.group(1).strip() if match else raw_sender.strip()

    subject = source_email.get("subject", "").strip()
    if not subject.lower().startswith("re:"):
        reply_subject = f"Re: {subject}" if subject else "Re: Follow up"
    else:
        reply_subject = subject

    snippet = source_email.get("snippet", "") or source_email.get("body", "")

    prompt = (
        f"You are drafting an email reply.\n"
        f"Original Email Sender: {raw_sender}\n"
        f"Original Email Subject: {subject}\n"
        f"Original Content: {snippet}\n"
        f"User's Instruction: {instruction}\n\n"
        f"Task: Write a concise, polite reply adhering to the instruction. "
        f"Write in the same language as the original email. "
        f"Return ONLY the body text of the reply draft."
    )

    from backend.brain import ask
    reply_body = ask([{"role": "user", "content": prompt}])

    return {
        "to": to_address,
        "subject": reply_subject,
        "body": reply_body.strip(),
        "source_email_id": source_email.get("id"),
    }
