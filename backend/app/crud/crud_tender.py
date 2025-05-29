from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.db.models.tender import Tender
from app.schemas.tender import TenderCreate, TenderUpdate


class CRUDTender(CRUDBase[Tender, TenderCreate, TenderUpdate]):
    async def get_with_items(
        self, 
        db: AsyncSession, 
        *, 
        id: UUID
    ) -> Optional[Tender]:
        result = await db.execute(
            select(Tender)
            .options(selectinload(Tender.items))
            .where(Tender.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_company(
        self, 
        db: AsyncSession, 
        *, 
        company_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Tender]:
        query = select(Tender).where(Tender.company_id == company_id)
        
        if status:
            query = query.where(Tender.status == status)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_tender_number(
        self, 
        db: AsyncSession, 
        *, 
        tender_number: str,
        company_id: UUID
    ) -> Optional[Tender]:
        result = await db.execute(
            select(Tender).where(
                and_(
                    Tender.tender_number == tender_number,
                    Tender.company_id == company_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_public_tenders(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0,
        limit: int = 100
    ) -> List[Tender]:
        result = await db.execute(
            select(Tender)
            .where(
                and_(
                    Tender.is_public == True,
                    Tender.status.in_(["PUBLISHED", "IN_PROGRESS", "QUOTE_PHASE"])
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_status(
        self, 
        db: AsyncSession, 
        *, 
        tender_id: UUID,
        status: str
    ) -> Optional[Tender]:
        tender = await self.get(db, id=tender_id)
        if tender:
            tender.status = status
            db.add(tender)
            await db.commit()
            await db.refresh(tender)
        return tender

    async def update_ai_analysis(
        self,
        db: AsyncSession,
        *,
        tender_id: UUID,
        processed_data: dict,
        risk_score: Optional[float] = None,
        ai_analysis: dict = None
    ) -> Optional[Tender]:
        tender = await self.get(db, id=tender_id)
        if tender:
            tender.processed_data = processed_data
            if risk_score is not None:
                tender.risk_score = risk_score
            if ai_analysis:
                tender.ai_analysis = ai_analysis
            
            db.add(tender)
            await db.commit()
            await db.refresh(tender)
        return tender

    async def get_pending_analysis(
        self, 
        db: AsyncSession,
        *, 
        limit: int = 10
    ) -> List[Tender]:
        """Busca editais pendentes de análise de IA"""
        result = await db.execute(
            select(Tender)
            .where(Tender.status == "ANALYZING")
            .limit(limit)
        )
        return result.scalars().all()


tender = CRUDTender(Tender)
