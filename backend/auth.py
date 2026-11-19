import hashlib
import logging
import os
import secrets
from typing import Optional, Set
from dotenv import load_dotenv

logger = logging.getLogger("aura.auth")
load_dotenv(override=True)

# In-memory valid session tokens (lost on restart, perfectly fine for single-user assistant)
VALID_SESSIONS: Set[str] = set()


def get_password_hash() -> Optional[str]:
    """Retrieve SHA-256 hash of AURA_PASSWORD from environment if configured."""
    load_dotenv(override=True)
    pw = os.getenv("AURA_PASSWORD")
    if not pw or not pw.strip():
        logger.info("AURA_PASSWORD is not set, dashboard is open (set it before deploying)")
        return None
    return hashlib.sha256(pw.strip().encode("utf-8")).hexdigest()


def is_auth_enabled() -> bool:
    """Return True if password protection is enabled via AURA_PASSWORD."""
    return get_password_hash() is not None


def verify_password(password: str) -> bool:
    """
    Hash-compare the submitted password with secrets.compare_digest against
    the SHA-256 hash of the env value. Never logs or stores plain password.
    """
    expected_hash = get_password_hash()
    if not expected_hash:
        # If no password is configured, access is open
        return True

    if not password:
        return False

    submitted_hash = hashlib.sha256(password.strip().encode("utf-8")).hexdigest()
    return secrets.compare_digest(submitted_hash, expected_hash)


def create_session_token() -> str:
    """Generate a secure random 32-byte hexadecimal session token."""
    return secrets.token_hex(32)


def add_session(token: str) -> None:
    """Register a valid session token in memory."""
    if token:
        VALID_SESSIONS.add(token)


def is_valid_session(token: Optional[str]) -> bool:
    """Check whether a session token is valid."""
    if not is_auth_enabled():
        return True
    if not token:
        return False
    return token in VALID_SESSIONS


def revoke_session(token: Optional[str]) -> None:
    """Remove a session token on logout."""
    if token and token in VALID_SESSIONS:
        VALID_SESSIONS.remove(token)
