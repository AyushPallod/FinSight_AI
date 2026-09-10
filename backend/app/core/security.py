import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

logger = logging.getLogger(__name__)

# ==========================================
# 1. Configuration Settings
# ==========================================
# SECRET_KEY is used to sign JWTs. In production, this MUST come from env settings.
SECRET_KEY = os.getenv(
    "SECRET_KEY", "super-secret-finsight-ai-key-do-not-use-in-production"
)
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ==========================================
# 2. Password Hashing (Bcrypt) - Step 2
# ==========================================
def get_password_hash(password: str) -> str:
    """
    Hashes a raw password using bcrypt and returns the decoded string hash.
    """
    # Generate a random salt
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain text password with a stored bcrypt hash.
    Returns True if match, False otherwise.
    """
    try:
        # bcrypt.checkpw requires bytes
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Error during password verification: {e!s}")
        return False


# ==========================================
# 3. JWT Token Management - Step 3
# ==========================================
def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Generates a short-lived JWT access token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "exp": expire,  # Expiration time claim
        "sub": str(subject),  # Subject claim (User ID)
        "type": "access",  # Token type marker
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """
    Generates a long-lived JWT refresh token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",  # Token type marker
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Returns the payload dictionary if valid, or an empty dictionary if expired/invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: Token has expired.")
        return {}
    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {e!s}")
        return {}
