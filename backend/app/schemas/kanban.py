"""
Kanban board, column, and card schemas.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.schemas.base import BaseSchema


# Kanban Board Schemas
class KanbanBoardBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    is_template: bool = Field(default=False)
    members: Optional[List[str]] = Field(default_factory=list)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class KanbanBoardCreate(KanbanBoardBase):
    pass


class KanbanBoardUpdate(KanbanBoardBase):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class KanbanBoardInDBBase(KanbanBoardBase, BaseSchema):
    company_id: str
    created_by: str


class KanbanBoardPublic(KanbanBoardInDBBase):
    pass


class KanbanBoardInDB(KanbanBoardInDBBase):
    pass


class KanbanBoardsPublic(BaseModel):
    data: List[KanbanBoardPublic]
    count: int


# Kanban Column Schemas
class KanbanColumnBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    position: int = Field(..., ge=0)
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$")
    wip_limit: Optional[int] = Field(None, ge=0)
    is_done_column: bool = Field(default=False)


class KanbanColumnCreate(KanbanColumnBase):
    board_id: str


class KanbanColumnUpdate(KanbanColumnBase):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = Field(None, ge=0)


class KanbanColumnInDBBase(KanbanColumnBase, BaseSchema):
    board_id: str


class KanbanColumnPublic(KanbanColumnInDBBase):
    cards_count: Optional[int] = None


class KanbanColumnInDB(KanbanColumnInDBBase):
    pass


class KanbanColumnsPublic(BaseModel):
    data: List[KanbanColumnPublic]
    count: int


# Kanban Card Schemas
class KanbanCardBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    position: int = Field(..., ge=0)
    priority: str = Field(default="MEDIUM")
    labels: Optional[List[str]] = Field(default_factory=list)
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    spent_hours: Optional[float] = Field(None, ge=0)
    checklist: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    attachments: Optional[List[str]] = Field(default_factory=list)

    @validator("priority")
    def validate_priority(cls, v):
        allowed_priorities = ["LOW", "MEDIUM", "HIGH", "URGENT"]
        if v not in allowed_priorities:
            raise ValueError(f"Priority must be one of: {allowed_priorities}")
        return v


class KanbanCardCreate(KanbanCardBase):
    column_id: str


class KanbanCardUpdate(KanbanCardBase):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[int] = Field(None, ge=0)
    column_id: Optional[str] = None


class KanbanCardInDBBase(KanbanCardBase, BaseSchema):
    column_id: str
    created_by: str


class KanbanCardPublic(KanbanCardInDBBase):
    pass


class KanbanCardInDB(KanbanCardInDBBase):
    pass


class KanbanCardsPublic(BaseModel):
    data: List[KanbanCardPublic]
    count: int


# Card Move Schema
class CardMoveRequest(BaseModel):
    target_column_id: str
    target_position: int


# Reorder Schemas
class PositionUpdate(BaseModel):
    id: str
    position: int


class ReorderRequest(BaseModel):
    items: List[PositionUpdate]


# Board with full structure
class KanbanBoardWithColumns(KanbanBoardPublic):
    columns: List[KanbanColumnPublic] = []


class KanbanColumnWithCards(KanbanColumnPublic):
    cards: List[KanbanCardPublic] = []


class KanbanBoardFull(KanbanBoardPublic):
    columns: List[KanbanColumnWithCards] = []


# Statistics
class KanbanStats(BaseModel):
    total_cards: int
    cards_by_column: Dict[str, int]
    cards_by_priority: Dict[str, int]


class KanbanBoardStats(KanbanStats):
    total_boards: int
    active_boards: int
