"""Login and current-user endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import AuthenticatedUser, get_auth_repository, get_current_user
from src.auth.jwt_handler import JWTError, create_access_token
from src.auth.schemas import CurrentUserResponse, LoginRequest, LoginResponse
from src.auth.security import verify_password
from src.database.repositories import DatabaseRepository


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def login_error():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=LoginResponse, summary="Log in and receive a JWT access token.")
def login(request: LoginRequest, repository: DatabaseRepository = Depends(get_auth_repository)):
    user = repository.get_user_by_email(request.email)
    if user is None or not user.is_active or not verify_password(request.password, user.password_hash):
        raise login_error()
    subject = user.customer.customer_id if user.customer else f"user:{user.id}"
    try:
        token = create_access_token(subject=subject, role=user.role)
        expires_in = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")) * 60
    except JWTError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is unavailable.") from error
    return LoginResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=CurrentUserResponse, summary="Return basic information for the authenticated user.")
def me(current_user: AuthenticatedUser = Depends(get_current_user)):
    return CurrentUserResponse(
        customer_id=current_user.customer_id,
        email=current_user.email,
        role=current_user.role,
    )
