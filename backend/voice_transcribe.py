"""
AURA Voice Transcription Helper.
Free audio transcription using the Gemini API (google-genai).
"""

import logging
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("aura.transcribe")

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
]

TRANSCRIBE_PROMPT = (
    "Transcribe this audio exactly, in its original language. "
    "Return only the transcription, no extra text."
)


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
    """
    Transcribes raw audio bytes using the Gemini API.
    Returns the transcription text, or None if transcription failed.
    """
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        logger.error("GEMINI_API_KEY is not set. Cannot transcribe audio.")
        return None

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    prompt_part = types.Part.from_text(text=TRANSCRIBE_PROMPT)
    contents = [part, prompt_part]

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
            if response and response.text:
                result = response.text.strip()
                logger.info(f"Transcription succeeded with {model_name}: '{result}'")
                return result
        except Exception as e:
            logger.warning(f"Transcription with model {model_name} failed: {e}")
            last_error = e
            continue

    if last_error:
        logger.error(f"All transcription candidate models failed: {last_error}")
    return None


def transcribe_audio_file(file_path: str, mime_type: str = "audio/ogg") -> Optional[str]:
    """
    Reads an audio file from disk, transcribes it, and returns the transcribed text.
    """
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
        return transcribe_audio_bytes(audio_bytes, mime_type=mime_type)
    except Exception as e:
        logger.error(f"Could not read audio file {file_path}: {e}")
        return None
