"""Small, reusable JWT creation and verification functions."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv


load_dotenv()


class JWTError(ValueError):
    """Raised for missing, expired, malformed, or invalid tokens."""


def _settings():
    secret = os.getenv("JWT_SECRET_KEY")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        expiration = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError as error:
        raise JWTError("JWT expiration configuration is invalid.") from error
    if not secret or secret == "change_this_in_production" or secret == "replace_with_a_long_random_secret":
        raise JWTError("JWT_SECRET_KEY is not configured.")
    return secret, algorithm, expiration


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    secret, algorithm, default_expiration = _settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes if expires_minutes is not None else default_expiration)
    return jwt.encode({"sub": subject, "role": role, "exp": expires_at}, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict:
    try:
        secret, algorithm, _ = _settings()
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise JWTError("Token subject is missing.")
        return payload
    except jwt.PyJWTError as error:
        raise JWTError("Token is invalid or expired.") from error
