"""
CRUD operations for quotes.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.db.models.quote import Quote
from app.schemas.quote import QuoteCreate, QuoteUpdate


class CRUDQuote(CRUDBase[Quote, QuoteCreate, QuoteUpdate]):
    async def get_with_items(
        self, db: AsyncSession, *, id: str
    ) -> Optional[Quote]:
        """Get quote with items."""
        stmt = (
            select(self.model)
            .options(selectinload(self.model.items))
            .where(self.model.id == id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_company(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Quote]:
        """Get quotes by company."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.is_active == True
                )
            )
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_tender(
        self,
        db: AsyncSession,
        *,
        tender_id: str,
        company_id: str,
    ) -> List[Quote]:
        """Get quotes by tender."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.tender_id == tender_id,
                    self.model.company_id == company_id,
                    self.model.is_active == True
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_multi_with_filters(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        status: Optional[str] = None,
        tender_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get quotes with filters."""
        # Base query
        stmt = select(self.model).where(
            and_(
                self.model.company_id == company_id,
                self.model.is_active == True
            )
        )
        count_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.company_id == company_id,
                self.model.is_active == True
            )
        )

        # Apply filters
        conditions = []
        
        if status:
            conditions.append(self.model.status == status)
        
        if tender_id:
            conditions.append(self.model.tender_id == tender_id)
        
        if created_by:
            conditions.append(self.model.created_by == created_by)
        
        if search:
            search_conditions = or_(
                self.model.title.ilike(f"%{search}%"),
                self.model.description.ilike(f"%{search}%"),
            )
            conditions.append(search_conditions)

        if conditions:
            filter_condition = and_(*conditions)
            stmt = stmt.where(filter_condition)
            count_stmt = count_stmt.where(filter_condition)

        # Get count
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()

        # Get data with relationships
        stmt = (
            stmt.options(
                selectinload(self.model.items),
                selectinload(self.model.tender),
            )
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        
        result = await db.execute(stmt)
        quotes = result.scalars().all()

        return {
            "data": quotes,
            "count": total_count,
        }

    async def get_pending_quotes(
        self,
        db: AsyncSession,
        *,
        company_id: str,
    ) -> List[Quote]:
        """Get pending quotes for a company."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.status == "DRAFT",
                    self.model.is_active == True
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_sent_quotes(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        days: int = 30,
    ) -> List[Quote]:
        """Get recently sent quotes."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.status.in_(["SENT", "RESPONDED"]),
                    self.model.sent_at >= cutoff_date,
                    self.model.is_active == True
                )
            )
            .order_by(self.model.sent_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_stats(
        self, db: AsyncSession, *, company_id: str
    ) -> Dict[str, Any]:
        """Get quote statistics for a company."""
        # Total quotes
        total_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.company_id == company_id,
                self.model.is_active == True
            )
        )
        total_result = await db.execute(total_stmt)
        total_quotes = total_result.scalar()

        # Quotes by status
        status_stmt = (
            select(self.model.status, func.count(self.model.id))
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.is_active == True
                )
            )
            .group_by(self.model.status)
        )
        status_result = await db.execute(status_stmt)
        status_counts = dict(status_result.all())

        # Average response time (in days)
        avg_response_stmt = select(
            func.avg(
                func.extract('epoch', self.model.responded_at - self.model.sent_at) / 86400
            )
        ).where(
            and_(
                self.model.company_id == company_id,
                self.model.responded_at.is_not(None),
                self.model.sent_at.is_not(None),
                self.model.is_active == True
            )
        )
        avg_response_result = await db.execute(avg_response_stmt)
        avg_response_time = avg_response_result.scalar() or 0

        return {
            "total_quotes": total_quotes,
            "quotes_by_status": status_counts,
            "average_response_time_days": round(avg_response_time, 2),
        }


quote = CRUDQuote(Quote)
