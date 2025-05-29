"""
User management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_user import user
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InsufficientPermissionsError,
)
from app.schemas.user import (
    UserCreate,
    UserInDB,
    UserPublic,
    UserUpdate,
    UsersPublic,
)

router = APIRouter()


@router.get("/", response_model=UsersPublic)
async def read_users(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> Any:
    """
    Retrieve users from the current user's company.
    Only ADMIN and SUPERUSER can access this endpoint.
    """
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise InsufficientPermissionsError("Not enough permissions")
    
    # If SUPERUSER, can see all users, if ADMIN only from their company
    company_id = None if current_user.role == "SUPERUSER" else current_user.company_id
    
    users_data = await user.get_multi_with_filters(
        db=db,
        skip=skip,
        limit=limit,
        company_id=company_id,
        search=search,
        role=role,
        is_active=is_active,
    )
    
    return UsersPublic(
        data=users_data["data"],
        count=users_data["count"]
    )


@router.post("/", response_model=UserPublic)
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_in: UserCreate,
) -> Any:
    """
    Create new user.
    Only ADMIN and SUPERUSER can create users.
    """
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise InsufficientPermissionsError("Not enough permissions")
    
    # Check if user already exists
    existing_user = await user.get_by_email(db=db, email=user_in.email)
    if existing_user:
        raise EntityAlreadyExistsError("User", "email", user_in.email)
    
    # If ADMIN, can only create users in their company
    if current_user.role == "ADMIN":
        user_in.company_id = current_user.company_id
    
    # Create user
    new_user = await user.create(db=db, obj_in=user_in)
    return new_user


@router.get("/{user_id}", response_model=UserPublic)
async def read_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_id: str,
) -> Any:
    """
    Get user by ID.
    """
    target_user = await user.get(db=db, id=user_id)
    if not target_user:
        raise EntityNotFoundError("User", user_id)
    
    # Check permissions
    if current_user.role == "USER":
        # Users can only see themselves
        if target_user.id != current_user.id:
            raise InsufficientPermissionsError("Not enough permissions")
    elif current_user.role == "ADMIN":
        # Admins can only see users from their company
        if target_user.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    # SUPERUSER can see all users
    
    return target_user


@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_id: str,
    user_in: UserUpdate,
) -> Any:
    """
    Update user.
    """
    target_user = await user.get(db=db, id=user_id)
    if not target_user:
        raise EntityNotFoundError("User", user_id)
    
    # Check permissions
    if current_user.role == "USER":
        # Users can only update themselves and limited fields
        if target_user.id != current_user.id:
            raise InsufficientPermissionsError("Not enough permissions")
        # Remove fields that regular users can't change
        user_in.role = None
        user_in.company_id = None
        user_in.is_active = None
    elif current_user.role == "ADMIN":
        # Admins can only update users from their company
        if target_user.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
        # Can't change company_id
        user_in.company_id = None
    # SUPERUSER can update all fields
    
    updated_user = await user.update(db=db, db_obj=target_user, obj_in=user_in)
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_id: str,
) -> Any:
    """
    Delete user (soft delete).
    Only ADMIN and SUPERUSER can delete users.
    """
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise InsufficientPermissionsError("Not enough permissions")
    
    target_user = await user.get(db=db, id=user_id)
    if not target_user:
        raise EntityNotFoundError("User", user_id)
    
    # Can't delete yourself
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Check permissions
    if current_user.role == "ADMIN":
        # Admins can only delete users from their company
        if target_user.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Soft delete
    await user.remove(db=db, id=user_id)
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/activate", response_model=UserPublic)
async def activate_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_id: str,
) -> Any:
    """
    Activate user.
    Only ADMIN and SUPERUSER can activate users.
    """
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise InsufficientPermissionsError("Not enough permissions")
    
    target_user = await user.get(db=db, id=user_id)
    if not target_user:
        raise EntityNotFoundError("User", user_id)
    
    # Check permissions
    if current_user.role == "ADMIN":
        if target_user.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_user = await user.update(
        db=db, 
        db_obj=target_user, 
        obj_in=UserUpdate(is_active=True)
    )
    return updated_user


@router.post("/{user_id}/deactivate", response_model=UserPublic)
async def deactivate_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_id: str,
) -> Any:
    """
    Deactivate user.
    Only ADMIN and SUPERUSER can deactivate users.
    """
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        raise InsufficientPermissionsError("Not enough permissions")
    
    target_user = await user.get(db=db, id=user_id)
    if not target_user:
        raise EntityNotFoundError("User", user_id)
    
    # Can't deactivate yourself
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Check permissions
    if current_user.role == "ADMIN":
        if target_user.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_user = await user.update(
        db=db, 
        db_obj=target_user, 
        obj_in=UserUpdate(is_active=False)
    )
    return updated_user


@router.get("/me/profile", response_model=UserInDB)
async def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user profile.
    """
    return current_user


@router.put("/me/profile", response_model=UserPublic)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    user_in: UserUpdate,
) -> Any:
    """
    Update own profile.
    """
    # Users can only update limited fields about themselves
    user_in.role = None
    user_in.company_id = None
    user_in.is_active = None
    
    updated_user = await user.update(db=db, db_obj=current_user, obj_in=user_in)
    return updated_user
