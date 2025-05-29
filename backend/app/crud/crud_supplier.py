"""
CRUD operations for suppliers.
"""
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.db.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class CRUDSupplier(CRUDBase[Supplier, SupplierCreate, SupplierUpdate]):
    async def get_by_email(
        self, db: AsyncSession, *, email: str
    ) -> Optional[Supplier]:
        """Get supplier by email."""
        stmt = select(self.model).where(
            and_(
                self.model.email == email,
                self.model.is_active == True
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_cnpj(
        self, db: AsyncSession, *, cnpj: str
    ) -> Optional[Supplier]:
        """Get supplier by CNPJ."""
        stmt = select(self.model).where(
            and_(
                self.model.cnpj == cnpj,
                self.model.is_active == True
            )
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
    ) -> List[Supplier]:
        """Get suppliers by company."""
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
            .order_by(self.model.name)
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
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get suppliers with filters."""
        # Base query
        stmt = select(self.model).where(self.model.company_id == company_id)
        count_stmt = select(func.count(self.model.id)).where(
            self.model.company_id == company_id
        )

        # Apply filters
        conditions = []
        
        if is_active is not None:
            conditions.append(self.model.is_active == is_active)
        
        if category:
            conditions.append(self.model.category == category)
        
        if search:
            search_conditions = or_(
                self.model.name.ilike(f"%{search}%"),
                self.model.email.ilike(f"%{search}%"),
                self.model.cnpj.ilike(f"%{search}%"),
                self.model.contact_person.ilike(f"%{search}%"),
            )
            conditions.append(search_conditions)

        if conditions:
            filter_condition = and_(*conditions)
            stmt = stmt.where(filter_condition)
            count_stmt = count_stmt.where(filter_condition)

        # Get count
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()

        # Get data
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        suppliers = result.scalars().all()

        return {
            "data": suppliers,
            "count": total_count,
        }

    async def search_by_products(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        product_keywords: List[str],
    ) -> List[Supplier]:
        """Search suppliers by products they offer."""
        # This would search in a products relationship or description field
        conditions = [self.model.company_id == company_id]
        
        for keyword in product_keywords:
            conditions.append(
                or_(
                    self.model.description.ilike(f"%{keyword}%"),
                    self.model.products.ilike(f"%{keyword}%"),  # If you have a products field
                )
            )

        stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(self.model.name)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_categories(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        categories: List[str],
    ) -> List[Supplier]:
        """Get suppliers by categories."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.category.in_(categories),
                    self.model.is_active == True
                )
            )
            .order_by(self.model.name)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_stats(
        self, db: AsyncSession, *, company_id: str
    ) -> Dict[str, Any]:
        """Get supplier statistics for a company."""
        # Total suppliers
        total_stmt = select(func.count(self.model.id)).where(
            self.model.company_id == company_id
        )
        total_result = await db.execute(total_stmt)
        total_suppliers = total_result.scalar()

        # Active suppliers
        active_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.company_id == company_id,
                self.model.is_active == True
            )
        )
        active_result = await db.execute(active_stmt)
        active_suppliers = active_result.scalar()

        # Suppliers by category
        category_stmt = (
            select(self.model.category, func.count(self.model.id))
            .where(
                and_(
                    self.model.company_id == company_id,
                    self.model.is_active == True
                )
            )
            .group_by(self.model.category)
        )
        category_result = await db.execute(category_stmt)
        categories = dict(category_result.all())

        return {
            "total_suppliers": total_suppliers,
            "active_suppliers": active_suppliers,
            "inactive_suppliers": total_suppliers - active_suppliers,
            "suppliers_by_category": categories,
        }


supplier = CRUDSupplier(Supplier)
