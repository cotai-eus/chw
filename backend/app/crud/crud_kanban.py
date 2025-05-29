"""
CRUD operations for kanban boards and cards.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.db.models.kanban import KanbanBoard, KanbanColumn, KanbanCard
from app.schemas.kanban import (
    KanbanBoardCreate,
    KanbanBoardUpdate,
    KanbanColumnCreate,
    KanbanColumnUpdate,
    KanbanCardCreate,
    KanbanCardUpdate,
)


class CRUDKanbanBoard(CRUDBase[KanbanBoard, KanbanBoardCreate, KanbanBoardUpdate]):
    async def get_with_columns_and_cards(
        self, db: AsyncSession, *, id: str
    ) -> Optional[KanbanBoard]:
        """Get board with columns and cards."""
        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.columns).selectinload(KanbanColumn.cards)
            )
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
    ) -> List[KanbanBoard]:
        """Get boards by company."""
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

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        company_id: str,
    ) -> List[KanbanBoard]:
        """Get boards where user is member or owner."""
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.company_id == company_id,
                    or_(
                        self.model.created_by == user_id,
                        self.model.members.contains([user_id])
                    ),
                    self.model.is_active == True
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()


class CRUDKanbanColumn(CRUDBase[KanbanColumn, KanbanColumnCreate, KanbanColumnUpdate]):
    async def get_by_board(
        self,
        db: AsyncSession,
        *,
        board_id: str,
    ) -> List[KanbanColumn]:
        """Get columns by board."""
        stmt = (
            select(self.model)
            .where(self.model.board_id == board_id)
            .order_by(self.model.position)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def reorder_columns(
        self,
        db: AsyncSession,
        *,
        board_id: str,
        column_positions: List[Dict[str, Any]],
    ) -> List[KanbanColumn]:
        """Reorder columns in a board."""
        for item in column_positions:
            column_id = item["id"]
            new_position = item["position"]
            
            stmt = select(self.model).where(
                and_(
                    self.model.id == column_id,
                    self.model.board_id == board_id
                )
            )
            result = await db.execute(stmt)
            column = result.scalar_one_or_none()
            
            if column:
                column.position = new_position
                db.add(column)
        
        await db.commit()
        
        # Return updated columns
        return await self.get_by_board(db, board_id=board_id)


class CRUDKanbanCard(CRUDBase[KanbanCard, KanbanCardCreate, KanbanCardUpdate]):
    async def get_by_column(
        self,
        db: AsyncSession,
        *,
        column_id: str,
    ) -> List[KanbanCard]:
        """Get cards by column."""
        stmt = (
            select(self.model)
            .where(self.model.column_id == column_id)
            .order_by(self.model.position)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_board(
        self,
        db: AsyncSession,
        *,
        board_id: str,
    ) -> List[KanbanCard]:
        """Get all cards in a board."""
        stmt = (
            select(self.model)
            .join(KanbanColumn)
            .where(KanbanColumn.board_id == board_id)
            .order_by(self.model.position)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_assignee(
        self,
        db: AsyncSession,
        *,
        assignee_id: str,
        company_id: str,
    ) -> List[KanbanCard]:
        """Get cards assigned to a user."""
        stmt = (
            select(self.model)
            .join(KanbanColumn)
            .join(KanbanBoard)
            .where(
                and_(
                    self.model.assignee_id == assignee_id,
                    KanbanBoard.company_id == company_id
                )
            )
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def move_card(
        self,
        db: AsyncSession,
        *,
        card_id: str,
        target_column_id: str,
        target_position: int,
    ) -> Optional[KanbanCard]:
        """Move card to different column and position."""
        # Get the card
        card = await self.get(db, id=card_id)
        if not card:
            return None

        # Update card position and column
        card.column_id = target_column_id
        card.position = target_position
        
        db.add(card)
        await db.commit()
        await db.refresh(card)
        
        return card

    async def reorder_cards(
        self,
        db: AsyncSession,
        *,
        column_id: str,
        card_positions: List[Dict[str, Any]],
    ) -> List[KanbanCard]:
        """Reorder cards within a column."""
        for item in card_positions:
            card_id = item["id"]
            new_position = item["position"]
            
            stmt = select(self.model).where(
                and_(
                    self.model.id == card_id,
                    self.model.column_id == column_id
                )
            )
            result = await db.execute(stmt)
            card = result.scalar_one_or_none()
            
            if card:
                card.position = new_position
                db.add(card)
        
        await db.commit()
        
        # Return updated cards
        return await self.get_by_column(db, column_id=column_id)

    async def get_stats(
        self, db: AsyncSession, *, board_id: str
    ) -> Dict[str, Any]:
        """Get card statistics for a board."""
        # Total cards
        total_stmt = (
            select(func.count(self.model.id))
            .join(KanbanColumn)
            .where(KanbanColumn.board_id == board_id)
        )
        total_result = await db.execute(total_stmt)
        total_cards = total_result.scalar()

        # Cards by status/column
        column_stmt = (
            select(KanbanColumn.title, func.count(self.model.id))
            .join(KanbanColumn)
            .where(KanbanColumn.board_id == board_id)
            .group_by(KanbanColumn.title)
        )
        column_result = await db.execute(column_stmt)
        cards_by_column = dict(column_result.all())

        # Cards by priority
        priority_stmt = (
            select(self.model.priority, func.count(self.model.id))
            .join(KanbanColumn)
            .where(KanbanColumn.board_id == board_id)
            .group_by(self.model.priority)
        )
        priority_result = await db.execute(priority_stmt)
        cards_by_priority = dict(priority_result.all())

        return {
            "total_cards": total_cards,
            "cards_by_column": cards_by_column,
            "cards_by_priority": cards_by_priority,
        }


kanban_board = CRUDKanbanBoard(KanbanBoard)
kanban_column = CRUDKanbanColumn(KanbanColumn)
kanban_card = CRUDKanbanCard(KanbanCard)
