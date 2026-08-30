"""FastAPI dependencies for Bearer-token authentication."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.jwt_handler import JWTError, decode_access_token
from src.database.database import get_session
from src.database.repositories import DatabaseRepository


bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Bearer JWT")


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    customer_id: str | None
    email: str
    role: str


def get_auth_repository():
    for session in get_session():
        yield DatabaseRepository(session)


def authentication_error():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    repository: DatabaseRepository = Depends(get_auth_repository),
) -> AuthenticatedUser:
    """Validate the token and then check the account still exists and is active."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error()
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as error:
        raise authentication_error() from error

    user = repository.get_user_by_subject(payload["sub"])
    if user is None or not user.is_active:
        raise authentication_error()
    customer_id = user.customer.customer_id if user.customer else None
    return AuthenticatedUser(user.id, customer_id, user.email, user.role)
