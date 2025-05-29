"""
Kanban board management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_kanban import kanban_board, kanban_column, kanban_card
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityNotFoundError,
    InsufficientPermissionsError,
    ValidationError,
)
from app.schemas.kanban import (
    KanbanBoardCreate,
    KanbanBoardUpdate,
    KanbanBoardPublic,
    KanbanBoardsPublic,
    KanbanBoardFull,
    KanbanColumnCreate,
    KanbanColumnUpdate,
    KanbanColumnPublic,
    KanbanColumnsPublic,
    KanbanCardCreate,
    KanbanCardUpdate,
    KanbanCardPublic,
    KanbanCardsPublic,
    CardMoveRequest,
    ReorderRequest,
    KanbanStats,
)

router = APIRouter()


# Board endpoints
@router.get("/boards", response_model=KanbanBoardsPublic)
async def read_boards(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> Any:
    """
    Retrieve kanban boards from the current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    boards = await kanban_board.get_by_company(
        db=db,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
    )
    
    return KanbanBoardsPublic(data=boards, count=len(boards))


@router.post("/boards", response_model=KanbanBoardPublic)
async def create_board(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_in: KanbanBoardCreate,
) -> Any:
    """
    Create new kanban board.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Set company_id and created_by
    board_data = board_in.dict()
    board_data["company_id"] = current_user.company_id
    board_data["created_by"] = current_user.id
    
    new_board = await kanban_board.create(db=db, obj_in=board_data)
    return new_board


@router.get("/boards/{board_id}", response_model=KanbanBoardFull)
async def read_board(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
) -> Any:
    """
    Get kanban board by ID with columns and cards.
    """
    target_board = await kanban_board.get_with_columns_and_cards(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
        
        # Check if user is member or owner
        if (target_board.created_by != current_user.id and 
            current_user.id not in (target_board.members or [])):
            raise InsufficientPermissionsError("You are not a member of this board")
    
    return target_board


@router.put("/boards/{board_id}", response_model=KanbanBoardPublic)
async def update_board(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
    board_in: KanbanBoardUpdate,
) -> Any:
    """
    Update kanban board.
    """
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
        
        # Only owner or admin can update board
        if (target_board.created_by != current_user.id and 
            current_user.role != "ADMIN"):
            raise InsufficientPermissionsError("Only board owner or admin can update")
    
    updated_board = await kanban_board.update(db=db, db_obj=target_board, obj_in=board_in)
    return updated_board


@router.delete("/boards/{board_id}")
async def delete_board(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
) -> Any:
    """
    Delete kanban board.
    """
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    # Check permissions
    if current_user.role not in ["ADMIN", "SUPERUSER"]:
        if target_board.created_by != current_user.id:
            raise InsufficientPermissionsError("Only board owner or admin can delete")
    elif current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    await kanban_board.remove(db=db, id=board_id)
    return {"message": "Board deleted successfully"}


# Column endpoints
@router.post("/boards/{board_id}/columns", response_model=KanbanColumnPublic)
async def create_column(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
    column_in: KanbanColumnCreate,
) -> Any:
    """
    Create new column in board.
    """
    # Verify board exists and user has access
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
        
        if (target_board.created_by != current_user.id and 
            current_user.id not in (target_board.members or [])):
            raise InsufficientPermissionsError("You are not a member of this board")
    
    # Set board_id
    column_in.board_id = board_id
    
    new_column = await kanban_column.create(db=db, obj_in=column_in)
    return new_column


@router.get("/boards/{board_id}/columns", response_model=KanbanColumnsPublic)
async def read_board_columns(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
) -> Any:
    """
    Get columns for a board.
    """
    # Verify board access first
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    columns = await kanban_column.get_by_board(db=db, board_id=board_id)
    return KanbanColumnsPublic(data=columns, count=len(columns))


@router.put("/columns/{column_id}", response_model=KanbanColumnPublic)
async def update_column(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    column_id: str,
    column_in: KanbanColumnUpdate,
) -> Any:
    """
    Update column.
    """
    target_column = await kanban_column.get(db=db, id=column_id)
    if not target_column:
        raise EntityNotFoundError("Column", column_id)
    
    # Verify board access
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_column = await kanban_column.update(db=db, db_obj=target_column, obj_in=column_in)
    return updated_column


@router.delete("/columns/{column_id}")
async def delete_column(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    column_id: str,
) -> Any:
    """
    Delete column.
    """
    target_column = await kanban_column.get(db=db, id=column_id)
    if not target_column:
        raise EntityNotFoundError("Column", column_id)
    
    # Verify board access
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    await kanban_column.remove(db=db, id=column_id)
    return {"message": "Column deleted successfully"}


# Card endpoints
@router.post("/columns/{column_id}/cards", response_model=KanbanCardPublic)
async def create_card(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    column_id: str,
    card_in: KanbanCardCreate,
) -> Any:
    """
    Create new card in column.
    """
    # Verify column exists and user has access
    target_column = await kanban_column.get(db=db, id=column_id)
    if not target_column:
        raise EntityNotFoundError("Column", column_id)
    
    # Verify board access
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Set column_id and created_by
    card_in.column_id = column_id
    card_data = card_in.dict()
    card_data["created_by"] = current_user.id
    
    new_card = await kanban_card.create(db=db, obj_in=card_data)
    return new_card


@router.get("/columns/{column_id}/cards", response_model=KanbanCardsPublic)
async def read_column_cards(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    column_id: str,
) -> Any:
    """
    Get cards for a column.
    """
    # Verify column access
    target_column = await kanban_column.get(db=db, id=column_id)
    if not target_column:
        raise EntityNotFoundError("Column", column_id)
    
    # Verify board access
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    cards = await kanban_card.get_by_column(db=db, column_id=column_id)
    return KanbanCardsPublic(data=cards, count=len(cards))


@router.put("/cards/{card_id}", response_model=KanbanCardPublic)
async def update_card(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    card_id: str,
    card_in: KanbanCardUpdate,
) -> Any:
    """
    Update card.
    """
    target_card = await kanban_card.get(db=db, id=card_id)
    if not target_card:
        raise EntityNotFoundError("Card", card_id)
    
    # Verify access through column and board
    target_column = await kanban_column.get(db=db, id=target_card.column_id)
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_card = await kanban_card.update(db=db, db_obj=target_card, obj_in=card_in)
    return updated_card


@router.post("/cards/{card_id}/move", response_model=KanbanCardPublic)
async def move_card(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    card_id: str,
    move_request: CardMoveRequest,
) -> Any:
    """
    Move card to different column and position.
    """
    target_card = await kanban_card.get(db=db, id=card_id)
    if not target_card:
        raise EntityNotFoundError("Card", card_id)
    
    # Verify access
    target_column = await kanban_column.get(db=db, id=target_card.column_id)
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Verify target column belongs to same board
    target_new_column = await kanban_column.get(db=db, id=move_request.target_column_id)
    if not target_new_column or target_new_column.board_id != target_board.id:
        raise ValidationError("Target column must belong to the same board")
    
    moved_card = await kanban_card.move_card(
        db=db,
        card_id=card_id,
        target_column_id=move_request.target_column_id,
        target_position=move_request.target_position,
    )
    
    return moved_card


@router.delete("/cards/{card_id}")
async def delete_card(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    card_id: str,
) -> Any:
    """
    Delete card.
    """
    target_card = await kanban_card.get(db=db, id=card_id)
    if not target_card:
        raise EntityNotFoundError("Card", card_id)
    
    # Verify access
    target_column = await kanban_column.get(db=db, id=target_card.column_id)
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
        
        # Only card creator, assignee, board owner, or admin can delete
        if (target_card.created_by != current_user.id and
            target_card.assignee_id != current_user.id and
            target_board.created_by != current_user.id and
            current_user.role != "ADMIN"):
            raise InsufficientPermissionsError("Not enough permissions to delete this card")
    
    await kanban_card.remove(db=db, id=card_id)
    return {"message": "Card deleted successfully"}


# Reorder endpoints
@router.post("/boards/{board_id}/reorder-columns")
async def reorder_columns(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
    reorder_request: ReorderRequest,
) -> Any:
    """
    Reorder columns in a board.
    """
    # Verify board access
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_columns = await kanban_column.reorder_columns(
        db=db,
        board_id=board_id,
        column_positions=reorder_request.items,
    )
    
    return {"data": updated_columns, "count": len(updated_columns)}


@router.post("/columns/{column_id}/reorder-cards")
async def reorder_cards(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    column_id: str,
    reorder_request: ReorderRequest,
) -> Any:
    """
    Reorder cards within a column.
    """
    # Verify column access
    target_column = await kanban_column.get(db=db, id=column_id)
    if not target_column:
        raise EntityNotFoundError("Column", column_id)
    
    # Verify board access
    target_board = await kanban_board.get(db=db, id=target_column.board_id)
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_cards = await kanban_card.reorder_cards(
        db=db,
        column_id=column_id,
        card_positions=reorder_request.items,
    )
    
    return {"data": updated_cards, "count": len(updated_cards)}


# Statistics
@router.get("/boards/{board_id}/stats", response_model=KanbanStats)
async def get_board_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    board_id: str,
) -> Any:
    """
    Get statistics for a board.
    """
    # Verify board access
    target_board = await kanban_board.get(db=db, id=board_id)
    if not target_board:
        raise EntityNotFoundError("Board", board_id)
    
    if current_user.role != "SUPERUSER":
        if target_board.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    stats = await kanban_card.get_stats(db=db, board_id=board_id)
    return stats


@router.get("/my/cards", response_model=KanbanCardsPublic)
async def get_my_cards(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get cards assigned to current user.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    my_cards = await kanban_card.get_by_assignee(
        db=db,
        assignee_id=current_user.id,
        company_id=current_user.company_id,
    )
    
    return KanbanCardsPublic(data=my_cards, count=len(my_cards))
