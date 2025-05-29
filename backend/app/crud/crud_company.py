from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.db.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CRUDCompany(CRUDBase[Company, CompanyCreate, CompanyUpdate]):
    async def get_by_cnpj(self, db: AsyncSession, *, cnpj: str) -> Optional[Company]:
        result = await db.execute(
            select(Company).where(Company.cnpj == cnpj)
        )
        return result.scalar_one_or_none()

    async def get_active_companies(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[Company]:
        result = await db.execute(
            select(Company)
            .where(Company.status == "ACTIVE")
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def activate_company(
        self, 
        db: AsyncSession, 
        *, 
        company_id: UUID
    ) -> Optional[Company]:
        company = await self.get(db, id=company_id)
        if company:
            company.status = "ACTIVE"
            company.is_verified = True
            db.add(company)
            await db.commit()
            await db.refresh(company)
        return company

    async def deactivate_company(
        self, 
        db: AsyncSession, 
        *, 
        company_id: UUID
    ) -> Optional[Company]:
        company = await self.get(db, id=company_id)
        if company:
            company.status = "INACTIVE"
            db.add(company)
            await db.commit()
            await db.refresh(company)
        return company


company = CRUDCompany(Company)
