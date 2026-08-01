"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.deps import CurrentUserDep
from backend.app.api.schemas import LoginRequest, LoginResponse, UserProfile
from backend.app.core.exceptions import UnauthorizedError
from backend.app.security.jwt import TOKEN_TYPE, create_access_token
from backend.app.security.users import authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    user = authenticate_user(body.email, body.password)
    if user is None:
        raise UnauthorizedError("Invalid email or password")

    token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
    )
    return LoginResponse(
        access_token=token,
        token_type=TOKEN_TYPE,
        role=user.role,
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )


@router.get("/me", response_model=UserProfile)
async def me(current_user: CurrentUserDep) -> UserProfile:
    return UserProfile(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        display_name=current_user.display_name,
    )
