"""Password hashing helpers. Passwords are never stored as plain text."""

from passlib.context import CryptContext


_password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bool(password and password_hash and _password_context.verify(password, password_hash))
