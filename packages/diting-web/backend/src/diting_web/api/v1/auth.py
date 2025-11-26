"""Authentication API - Simplified."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_user_from_refresh_token,
    verify_password,
)
from diting_web.common.response import success_response
from diting_web.config import settings
from diting_web.db.session import get_db
from diting_web.models.user import User
from diting_web.schemas.user import TokenResponse, UserLogin, UserResponse

router = APIRouter(prefix="/auth")


# Note: User registration is disabled. Only admins can create users via /api/v1/users


@router.post("/login")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """User login endpoint.
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        Success response with tokens and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Query user by username
    result = await db.execute(
        select(User).where(User.username == login_data.username)
    )
    user = result.scalar_one_or_none()

    # Verify credentials
    if user is None or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Update last login time
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # User response
    user_response = UserResponse.model_validate(user)

    # Return token response
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user_response,
    )

    return success_response(data=token_response.model_dump())


@router.post("/refresh")
async def refresh_token(
    user: User = Depends(get_user_from_refresh_token),
) -> dict:
    """Refresh access token using refresh token.
    
    Args:
        user: User from refresh token
        
    Returns:
        New access token
    """
    # Create new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )
    
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }
    )


@router.get("/me")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User info
    """
    user_data = UserResponse.model_validate(current_user).model_dump()
    
    return success_response(data=user_data)

