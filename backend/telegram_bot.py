import logging
import os
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from backend.approvals import (
    approve as approvals_approve,
    get_action,
    list_pending,
    reject as approvals_reject,
)
from backend.brain import ask, is_configured
from backend.connectors.calendar import (
    execute_create_event,
    get_status as calendar_status,
)
from backend.connectors.gmail import get_status as gmail_status
from backend.memory import get as memory_get, set_val as memory_set
from backend.voice_transcribe import transcribe_audio_file

logger = logging.getLogger("aura.telegram")
load_dotenv()

# In-memory per-user chat history: user_id -> list of {role, content}
user_histories: Dict[int, List[dict]] = defaultdict(list)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with a clean introduction and save telegram_chat_id."""
    chat_id = str(update.effective_chat.id) if update.effective_chat else None
    if chat_id:
        existing_chat_id = memory_get("telegram_chat_id")
        if not existing_chat_id:
            memory_set("telegram_chat_id", chat_id)
            logger.info(f"Saved telegram_chat_id: {chat_id}")
        elif existing_chat_id != chat_id:
            logger.warning(
                f"Existing telegram_chat_id is {existing_chat_id}, not overwriting with {chat_id} without asking."
            )

    text = (
        "AURA — Personal Agent\n\n"
        "I am your voice-first personal AI assistant. "
        "I help you manage emails, check calendar events, and review pending actions.\n\n"
        "Available commands:\n"
        "/status — Check system connectivity\n"
        "/approvals — Review pending actions\n"
        "/lang — Choose preferred language (English, Kannada, Hindi, Telugu)\n"
        "/help — Guidance and instructions\n\n"
        "You can send me any message to chat."
    )
    if update.message:
        await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    text = (
        "AURA Commands:\n"
        "/status — Check Brain, Gmail, Calendar, and pending approvals\n"
        "/approvals — List pending actions with inline Approve/Reject buttons\n"
        "/lang — Choose preferred language (English, Kannada, Hindi, Telugu)\n"
        "/start — Restart or view the welcome overview\n\n"
        "Type any message to chat with AURA. Sensitive actions always require explicit approval."
    )
    if update.message:
        await update.message.reply_text(text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    brain_ok = "Configured" if is_configured() else "Not configured"
    gmail_ok = "Connected" if gmail_status().get("connected") else "Not connected"
    cal_ok = "Connected" if calendar_status().get("connected") else "Not connected"
    pending_count = len(list_pending())

    status_text = (
        "AURA System Status:\n"
        f"• Brain: {brain_ok}\n"
        f"• Gmail: {gmail_ok}\n"
        f"• Calendar: {cal_ok}\n"
        f"• Pending Approvals: {pending_count}"
    )
    if update.message:
        await update.message.reply_text(status_text)


async def approvals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approvals command."""
    pending = list_pending()
    if not pending:
        if update.message:
            await update.message.reply_text("No pending approvals.")
        return

    for act in pending:
        keyboard = [
            [
                InlineKeyboardButton(
                    "Approve", callback_data=f"approve_{act['id']}"
                ),
                InlineKeyboardButton(
                    "Reject", callback_data=f"reject_{act['id']}"
                ),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = (
            f"Approval #{act['id']} [{act['action_type']}]\n"
            f"{act['summary']}"
        )
        if update.message:
            await update.message.reply_text(msg_text, reply_markup=reply_markup)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks for Approvals (one-shot)."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""
    if data.startswith("approve_"):
        try:
            action_id = int(data.split("_")[1])
            updated = approvals_approve(action_id)

            # Auto-execute calendar event if connected
            if updated.get("action_type") == "CREATE_CALENDAR_EVENT":
                cal_stat = calendar_status()
                if cal_stat.get("connected"):
                    execute_create_event(action_id)

            await query.edit_message_text(
                f"Action #{action_id} approved successfully."
            )
        except ValueError:
            await query.edit_message_text("already approved/rejected")
        except Exception as e:
            await query.edit_message_text(f"Approval error: {str(e)}")

    elif data.startswith("reject_"):
        try:
            action_id = int(data.split("_")[1])
            approvals_reject(action_id)
            await query.edit_message_text(f"Action #{action_id} rejected.")
        except ValueError:
            await query.edit_message_text("already approved/rejected")
        except Exception as e:
            await query.edit_message_text(f"Rejection error: {str(e)}")

    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        lang_names = {
            "en-IN": "English",
            "kn-IN": "Kannada",
            "hi-IN": "Hindi",
            "te-IN": "Telugu",
        }
        chosen_name = lang_names.get(lang_code, "English")
        memory_set("preferred_language", lang_code)
        memory_set("language", chosen_name)
        await query.edit_message_text(f"Language set to {chosen_name}.")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command with inline language buttons."""
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en-IN"),
            InlineKeyboardButton("ಕನ್ನಡ (Kannada)", callback_data="lang_kn-IN"),
        ],
        [
            InlineKeyboardButton("हिंदी (Hindi)", callback_data="lang_hi-IN"),
            InlineKeyboardButton("తెలుగు (Telugu)", callback_data="lang_te-IN"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Choose your preferred language:", reply_markup=reply_markup)


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming Telegram voice notes:
    - Downloads the OGG Opus voice file to a unique temp file.
    - Transcribes it for free using Gemini API.
    - Deletes the temporary file immediately after transcription.
    - Feeds the transcribed text into brain.ask() and replies in Telegram.
    - If transcription fails, politely asks the user to try again or type.
    """
    if not update.message or not update.message.voice:
        return

    tmp_dir = Path("/tmp") if os.path.exists("/tmp") else Path(tempfile.gettempdir())
    unique_name = f"aura_voice_{uuid.uuid4().hex}.oga"
    tmp_path = tmp_dir / unique_name
    transcription = None

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        await voice_file.download_to_drive(custom_path=tmp_path)
        transcription = transcribe_audio_file(str(tmp_path), mime_type="audio/ogg")
    except Exception as e:
        logger.error(f"Error handling voice note download/transcription: {e}")
        transcription = None
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp voice file {tmp_path}: {e}")

    if not transcription or not transcription.strip():
        await update.message.reply_text("I couldn't understand that voice note. Please try again or type it.")
        return

    user_text = transcription.strip()
    logger.info(f"Telegram voice note transcribed: '{user_text}'")

    user_id = update.effective_user.id if update.effective_user else 0
    history = user_histories[user_id]
    messages = list(history) + [{"role": "user", "content": user_text}]

    try:
        reply = ask(messages)
        if not reply:
            reply = "I received your voice note, but had trouble generating a reply."

        history.append({"role": "user", "content": user_text})
        history.append({"role": "model", "content": reply})
        if len(history) > 20:
            user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error processing transcribed voice note in brain: {e}")
        await update.message.reply_text(f"AURA Error: {str(e)}")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal user text messages with multi-turn brain context."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id if update.effective_user else 0
    user_text = update.message.text.strip()
    if not user_text:
        return

    history = user_histories[user_id]
    messages = list(history) + [{"role": "user", "content": user_text}]

    try:
        reply = ask(messages)
        if not reply:
            reply = "I received your message, but had trouble generating a reply."

        # Update user history (keep last 20 messages)
        history.append({"role": "user", "content": user_text})
        history.append({"role": "model", "content": reply})
        if len(history) > 20:
            user_histories[user_id] = history[-20:]

        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Error processing Telegram message: {e}")
        await update.message.reply_text(f"AURA Error: {str(e)}")


def create_bot_app() -> Optional[Application]:
    """Create and configure the Telegram bot application."""
    load_dotenv(override=True)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not token.strip():
        print(
            "TELEGRAM_BOT_TOKEN is not set. Get one from @BotFather and put it in .env"
        )
        return None

    app = ApplicationBuilder().token(token.strip()).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("approvals", approvals_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    return app
