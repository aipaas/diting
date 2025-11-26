"""User management API - Simplified (Admin Only)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from diting_web.auth import get_password_hash, require_admin
from diting_web.common.response import success_response
from diting_web.db.session import get_db
from diting_web.models.user import User

router = APIRouter(prefix="/users")


# ============================================================================
# Schemas
# ============================================================================

class UserCreate(BaseModel):
    """User creation schema (admin only)."""
    username: str
    email: Optional[str] = None
    password: str
    full_name: Optional[str] = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    """User update schema (admin only)."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: str
    
    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new user (Admin only).
    
    Args:
        user_data: User creation data
        db: Database session
        
    Returns:
        Success response with user info
        
    Raises:
        HTTPException: If username or email already exists
    """
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )
    
    # Check if email exists (only if email is provided)
    if user_data.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已存在",
            )
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_admin=user_data.is_admin,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return success_response(
        data={
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "is_admin": new_user.is_admin,
            "message": "用户创建成功",
        },
        code=201,
    )


@router.get("", dependencies=[Depends(require_admin)])
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_admin: Optional[bool] = Query(None, description="过滤管理员"),
    is_active: Optional[bool] = Query(None, description="过滤激活状态"),
    search: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get user list (Admin only).
    
    Args:
        page: Page number
        page_size: Items per page
        is_admin: Filter by admin status
        is_active: Filter by active status
        search: Search by username or email
        db: Database session
        
    Returns:
        Paginated user list
    """
    # Build query
    query = select(User)
    
    # Apply filters
    if is_admin is not None:
        query = query.where(User.is_admin == is_admin)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        search_conditions = [User.username.ilike(f"%{search}%")]
        # Only search email if it's not null
        search_conditions.append(User.email.ilike(f"%{search}%"))
        query = query.where(or_(*search_conditions))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return success_response(
        data={
            "items": [
                {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                }
                for user in users
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }
    )


@router.get("/{user_id}", dependencies=[Depends(require_admin)])
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get user details (Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        User details
        
    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    return success_response(
        data={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_email_verified": user.is_email_verified,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
    )


@router.put("/{user_id}", dependencies=[Depends(require_admin)])
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update user (Admin only).
    
    Args:
        user_id: User ID
        user_data: User update data
        db: Database session
        
    Returns:
        Success response with updated user info
        
    Raises:
        HTTPException: If user not found or email already exists
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # Check email uniqueness if changing
    if user_data.email and user_data.email != user.email:
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已存在",
            )
        user.email = user_data.email
    
    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin
    
    await db.commit()
    await db.refresh(user)
    
    return success_response(
        data={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "message": "用户更新成功",
        }
    )


@router.delete("/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """Delete user (Admin only).
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If user not found or trying to delete self
    """
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # Delete user (will cascade to resources with created_by)
    await db.delete(user)
    await db.commit()
    
    return success_response(
        data={
            "message": "用户删除成功",
            "deleted_user_id": str(user_id),
        }
    )


@router.post("/{user_id}/reset-password", dependencies=[Depends(require_admin)])
async def reset_user_password(
    user_id: UUID,
    new_password: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reset user password (Admin only).
    
    Args:
        user_id: User ID
        new_password: New password
        db: Database session
        
    Returns:
        Success response
        
    Raises:
        HTTPException: If user not found
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # Reset password
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    
    return success_response(
        data={
            "message": "密码重置成功",
            "user_id": str(user_id),
        }
    )

