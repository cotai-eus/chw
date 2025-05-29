from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    elif not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Criar refresh token e sessão
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = security.create_refresh_token(
        user.email, expires_delta=refresh_token_expires
    )
    
    # Criar sessão no banco
    session = await crud.user_session.create_session(
        db,
        user_id=user.id,
        token_hash=security.get_password_hash(refresh_token),
        expires_in_days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    # Criar access token com session_id
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.email, 
        expires_delta=access_token_expires,
        session_id=str(session.id)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    db: AsyncSession = Depends(get_db),
    refresh_data: schemas.RefreshTokenRequest = None
) -> Any:
    """
    Refresh access token using refresh token
    """
    payload = security.decode_access_token(refresh_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verificar se a sessão ainda é válida
    token_hash = security.get_password_hash(refresh_data.refresh_token)
    session = await crud.user_session.get_by_token_hash(db, token_hash=token_hash)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Buscar usuário
    user = await crud.user.get_by_email(db, email=email)
    if not user or not crud.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Criar novo access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.email,
        expires_delta=access_token_expires,
        session_id=str(session.id)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_data.refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Logout user and invalidate all sessions
    """
    await crud.user_session.invalidate_all_user_sessions(
        db, user_id=current_user.id
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.post("/change-password")
async def change_password(
    *,
    db: AsyncSession = Depends(get_db),
    password_data: schemas.UserChangePassword,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Change password
    """
    if not security.verify_password(
        password_data.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    await crud.user.change_password(
        db, user=current_user, new_password=password_data.new_password
    )
    
    return {"message": "Password updated successfully"}
