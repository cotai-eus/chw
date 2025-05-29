from typing import Any, Dict, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_profile(self, db: AsyncSession, *, id: UUID) -> Optional[User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        obj_in_data = obj_in.dict()
        password = obj_in_data.pop("password")
        obj_in_data["password_hash"] = get_password_hash(password)
        
        db_obj = User(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        # Se tiver nova senha, fazer o hash
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["password_hash"] = hashed_password
        
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> Optional[User]:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        return user.is_active and user.status == "ACTIVE"

    async def is_superuser(self, user: User) -> bool:
        return user.role == "MASTER"

    async def get_by_company(
        self, 
        db: AsyncSession, 
        *, 
        company_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        result = await db.execute(
            select(User)
            .where(User.company_id == company_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def change_password(
        self, 
        db: AsyncSession, 
        *, 
        user: User, 
        new_password: str
    ) -> User:
        hashed_password = get_password_hash(new_password)
        user.password_hash = hashed_password
        user.must_change_password = False
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


user = CRUDUser(User)
