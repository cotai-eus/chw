from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.crud import crud_models
from app.db import models
from app.db.session import get_db
from app.schemas.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    user = await crud_models.user.get_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    
    if not crud_models.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not crud_models.user.is_superuser(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user doesn't have enough privileges"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory para verificar roles específicos
    """
    async def role_checker(
        current_user: models.User = Depends(get_current_active_user)
    ) -> models.User:
        if (current_user.role != required_role and 
            current_user.role != UserRole.MASTER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


def require_company_access(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    """
    Verifica se o usuário tem acesso à empresa
    """
    if not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with any company"
        )
    return current_user


async def get_current_user_company(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
) -> models.Company:
    """
    Retorna a empresa do usuário atual
    """
    company = await crud_models.company.get(db, id=current_user.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return company
