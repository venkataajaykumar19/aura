import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

from backend.tools import (
    get_today_events,
    get_recent_emails,
    request_calendar_event,
    request_send_email,
    get_facts,
    save_fact,
    log_expense,
    save_note,
    search_notes,
)

load_dotenv()
logger = logging.getLogger("aura.brain")

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
]

BASE_SYSTEM_INSTRUCTION = (
    "You are AURA, a calm, editorial, voice-first personal AI assistant. "
    "You help the user manage email, calendar, reminders, expenses, and notes. "
    "CRITICAL APPROVAL-FIRST RULE: You must NEVER execute a sensitive action directly "
    "(such as sending an email or creating a calendar event). Always use request_calendar_event "
    "or request_send_email, which create pending approvals for the user to review. "
    "When the user mentions spending or paying money (e.g. 'spent 200 on lunch', 'paid 150 for coffee'), "
    "call the log_expense tool with the amount, category (Food, Travel, Shopping, Bills, or Other), and note. "
    "When the user asks you to save or remember a note (e.g. 'note that ...', 'save a note ...', 'remember this note ...'), "
    "call the save_note tool with the content. "
    "When the user asks about their notes (e.g. 'what did I note about ...?', 'find my notes on ...', 'show my notes'), "
    "call search_notes tool to retrieve them and quote or summarize what you find. "
    "Logging expenses and saving/searching notes do NOT require approval. "
    "If Google Calendar or Gmail is not connected according to the tools, state plainly that "
    "it is not connected; never invent fake events or emails. "
    "Keep replies short, calm, and natural (1-3 sentences max). Never use emoji spam or chatty filler."
)


class MissingApiKeyError(Exception):
    """Raised when the GEMINI_API_KEY environment variable is not configured."""
    pass


def is_configured() -> bool:
    """Check if GEMINI_API_KEY is configured in the environment."""
    load_dotenv(override=True)
    key = os.getenv("GEMINI_API_KEY")
    return bool(key and key.strip())


def try_handle_remember_phrase(text: str) -> Optional[str]:
    """
    Directly handle natural memory triggers:
    'remember that my <X> is <Y>', 'remember my <X> is <Y>', 'remember that <X>'
    Saves the fact and returns a short confirmation sentence.
    """
    clean = text.strip()

    # Pattern 1: 'remember that my <X> is <Y>' or 'remember my <X> is <Y>'
    m1 = re.match(r"^remember\s+(?:that\s+)?my\s+(.+?)\s+is\s+(.+)$", clean, re.IGNORECASE)
    if m1:
        key = m1.group(1).strip().lower()
        val = m1.group(2).strip().rstrip(".!")
        save_fact(key, val)
        return f"I'll remember that your {key} is {val}."

    # Pattern 2: 'remember that <X> is <Y>'
    m2 = re.match(r"^remember\s+that\s+(.+?)\s+is\s+(.+)$", clean, re.IGNORECASE)
    if m2:
        key = m2.group(1).strip().lower()
        val = m2.group(2).strip().rstrip(".!")
        save_fact(key, val)
        return f"I'll remember that {key} is {val}."

    # Pattern 3: 'remember that <X>'
    m3 = re.match(r"^remember\s+that\s+(.+)$", clean, re.IGNORECASE)
    if m3:
        fact = m3.group(1).strip().rstrip(".!")
        save_fact("note", fact)
        return f"I'll remember that {fact}."

    return None


def try_handle_expense_phrase(text: str) -> Optional[str]:
    """
    Directly handle common expense voice/chat triggers:
    'spent 200 on lunch', 'I spent 500 for petrol', 'paid 150 for coffee', 'spent 100 on groceries'
    """
    clean = text.strip()
    m = re.match(r"^(?:i\s+)?(?:spent|paid)\s+(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)\s+(?:on|for)\s+(.+)$", clean, re.IGNORECASE)
    if m:
        try:
            amt = float(m.group(1))
            note = m.group(2).strip().rstrip(".!")
            from backend.expenses import normalize_category
            cat = normalize_category(note)
            res = log_expense(amount=amt, category=cat, note=note)
            return f"Logged ₹{amt:.0f} for {cat} ({note}). You've spent ₹{res['total_spent_today']:.0f} today."
        except Exception as e:
            logger.warning(f"Error in direct expense handler: {e}")
    return None


def try_handle_note_phrase(text: str) -> Optional[str]:
    """
    Directly handle common note triggers:
    'note that ...', 'save a note that ...', 'remember this note ...'
    """
    clean = text.strip()
    m = re.match(r"^(?:please\s+)?(?:note\s+that|save\s+(?:a\s+)?note(?:\s+that)?|remember\s+this\s+note(?:\s+that)?)\s+(.+)$", clean, re.IGNORECASE)
    if m:
        try:
            content = m.group(1).strip()
            res = save_note(title="", content=content)
            return f"Saved note: '{res['note']['title']}'."
        except Exception as e:
            logger.warning(f"Error in direct note handler: {e}")
    return None


LANGUAGE_NAMES = {
    "en-IN": "English",
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "te-IN": "Telugu",
    "english": "English",
    "kannada": "Kannada",
    "hindi": "Hindi",
    "telugu": "Telugu",
}


def get_user_preferred_language() -> str:
    """Retrieve the user's preferred language from memory preferences."""
    from backend.memory import get as memory_get
    pref = memory_get("preferred_language") or memory_get("language") or "en-IN"
    return LANGUAGE_NAMES.get(pref, LANGUAGE_NAMES.get(pref.lower(), "English"))


def build_system_prompt() -> str:
    """
    Build system prompt with current date/time, language instruction, and remembered facts.
    Only includes facts that exist, no fake facts.
    """
    now = datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")
    lang_name = get_user_preferred_language()

    lines = [
        BASE_SYSTEM_INSTRUCTION,
        f"\nCurrent date: {date_str}. Current local time: {time_str}.",
        f"Reply in the user's preferred language ({lang_name}) unless the user writes in a different language.",
    ]

    facts = get_facts()
    if facts:
        lines.append("\nThings to remember about the user:")
        for k, v in facts.items():
            lines.append(f"- {k}: {v}")

    return "\n".join(lines)


def ask(messages: List[Dict[str, str]]) -> str:
    """
    Process conversation history and return AURA's response.
    Loads facts on every turn and supports tool use with Gemini function calling.
    Max 3 tool steps per reply.
    """
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise MissingApiKeyError(
            "GEMINI_API_KEY is not set. Get a free key from Google AI Studio and put it in .env"
        )

    # 1. Check if the latest user message is an explicit memory or expense instruction
    if messages:
        last_msg = messages[-1]
        if last_msg.get("role") == "user":
            user_text = last_msg.get("content", "")
            remember_reply = try_handle_remember_phrase(user_text)
            if remember_reply:
                return remember_reply
            expense_reply = try_handle_expense_phrase(user_text)
            if expense_reply:
                return expense_reply
            note_reply = try_handle_note_phrase(user_text)
            if note_reply:
                return note_reply

    # 2. Build Gemini client & content
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    formatted_contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        mapped_role = "model" if role in ("assistant", "model") else "user"
        formatted_contents.append(
            types.Content(
                role=mapped_role,
                parts=[types.Part.from_text(text=content)]
            )
        )

    # Available tools for Gemini function calling
    gemini_tools = [
        get_today_events,
        get_recent_emails,
        request_calendar_event,
        request_send_email,
        save_fact,
        log_expense,
        save_note,
        search_notes,
    ]

    config = types.GenerateContentConfig(
        system_instruction=build_system_prompt(),
        tools=gemini_tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=3
        ),
    )

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=formatted_contents,
                config=config,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            last_error = e
            continue

    if last_error:
        raise last_error

    return ""
