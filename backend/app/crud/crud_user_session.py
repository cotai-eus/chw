from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.db.models.user_session import UserSession
from app.schemas.token import TokenPayload


class CRUDUserSession(CRUDBase[UserSession, dict, dict]):
    async def get_by_token_hash(
        self, 
        db: AsyncSession, 
        *, 
        token_hash: str
    ) -> Optional[UserSession]:
        result = await db.execute(
            select(UserSession).where(
                and_(
                    UserSession.token_hash == token_hash,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_sessions(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID
    ) -> List[UserSession]:
        result = await db.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalars().all()

    async def create_session(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        token_hash: str,
        device_fingerprint: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        expires_in_days: int = 30
    ) -> UserSession:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            device_fingerprint=device_fingerprint,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
            last_activity=datetime.utcnow()
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def invalidate_session(
        self, 
        db: AsyncSession, 
        *, 
        session_id: UUID
    ) -> Optional[UserSession]:
        session = await self.get(db, id=session_id)
        if session:
            session.is_active = False
            db.add(session)
            await db.commit()
            await db.refresh(session)
        return session

    async def invalidate_all_user_sessions(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID
    ) -> int:
        sessions = await self.get_active_sessions(db, user_id=user_id)
        count = 0
        for session in sessions:
            session.is_active = False
            db.add(session)
            count += 1
        
        if count > 0:
            await db.commit()
        return count

    async def update_last_activity(
        self, 
        db: AsyncSession, 
        *, 
        session_id: UUID
    ) -> Optional[UserSession]:
        session = await self.get(db, id=session_id)
        if session and session.is_active:
            session.last_activity = datetime.utcnow()
            db.add(session)
            await db.commit()
            await db.refresh(session)
        return session

    async def cleanup_expired_sessions(self, db: AsyncSession) -> int:
        """Remove sessões expiradas"""
        result = await db.execute(
            select(UserSession).where(
                UserSession.expires_at < datetime.utcnow()
            )
        )
        expired_sessions = result.scalars().all()
        
        count = 0
        for session in expired_sessions:
            await db.delete(session)
            count += 1
        
        if count > 0:
            await db.commit()
        return count

    async def count_user_sessions(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID
    ) -> int:
        """Conta sessões ativas do usuário"""
        active_sessions = await self.get_active_sessions(db, user_id=user_id)
        return len(active_sessions)


user_session = CRUDUserSession(UserSession)
