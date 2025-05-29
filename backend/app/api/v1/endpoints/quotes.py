"""
Quote management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_quote import quote
from app.crud.crud_tender import tender
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityNotFoundError,
    InsufficientPermissionsError,
    ValidationError,
)
from app.schemas.quote import (
    QuoteCreate,
    QuoteInDB,
    QuotePublic,
    QuoteUpdate,
    QuotesPublic,
)
from app.services.quote_service import QuoteService
from app.services.email_service import EmailService

router = APIRouter()


@router.get("/", response_model=QuotesPublic)
async def read_quotes(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tender_id: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
) -> Any:
    """
    Retrieve quotes from the current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    quotes_data = await quote.get_multi_with_filters(
        db=db,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
        search=search,
        status=status,
        tender_id=tender_id,
        created_by=created_by,
    )
    
    return QuotesPublic(
        data=quotes_data["data"],
        count=quotes_data["count"]
    )


@router.post("/", response_model=QuotePublic)
async def create_quote(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    quote_in: QuoteCreate,
) -> Any:
    """
    Create new quote.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Verify tender exists and belongs to the company
    if quote_in.tender_id:
        target_tender = await tender.get(db=db, id=quote_in.tender_id)
        if not target_tender:
            raise EntityNotFoundError("Tender", quote_in.tender_id)
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Tender does not belong to your company")
    
    # Set company_id and created_by
    quote_in.company_id = current_user.company_id
    quote_in.created_by = current_user.id
    
    new_quote = await quote.create(db=db, obj_in=quote_in)
    return new_quote


@router.post("/generate", response_model=QuotePublic)
async def generate_quote_from_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_id: str,
    title: Optional[str] = None,
) -> Any:
    """
    Generate quote automatically from tender data.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Verify tender exists and belongs to the company
    target_tender = await tender.get_with_items(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    if target_tender.company_id != current_user.company_id:
        raise InsufficientPermissionsError("Tender does not belong to your company")
    
    if target_tender.status != "PROCESSED":
        raise ValidationError("Tender must be processed before generating quotes")
    
    # Generate quote using service
    quote_service = QuoteService()
    new_quote = await quote_service.generate_from_tender(
        db=db,
        tender=target_tender,
        user_id=current_user.id,
        title=title
    )
    
    return new_quote


@router.get("/{quote_id}", response_model=QuotePublic)
async def read_quote(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    quote_id: str,
) -> Any:
    """
    Get quote by ID.
    """
    target_quote = await quote.get_with_items(db=db, id=quote_id)
    if not target_quote:
        raise EntityNotFoundError("Quote", quote_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_quote.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    return target_quote


@router.put("/{quote_id}", response_model=QuotePublic)
async def update_quote(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    quote_id: str,
    quote_in: QuoteUpdate,
) -> Any:
    """
    Update quote.
    """
    target_quote = await quote.get(db=db, id=quote_id)
    if not target_quote:
        raise EntityNotFoundError("Quote", quote_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_quote.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Can't update sent quotes
    if target_quote.status in ["SENT", "RESPONDED"]:
        raise ValidationError("Cannot update quotes that have been sent")
    
    updated_quote = await quote.update(db=db, db_obj=target_quote, obj_in=quote_in)
    return updated_quote


@router.delete("/{quote_id}")
async def delete_quote(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    quote_id: str,
) -> Any:
    """
    Delete quote (soft delete).
    """
    target_quote = await quote.get(db=db, id=quote_id)
    if not target_quote:
        raise EntityNotFoundError("Quote", quote_id)
    
    # Check permissions
    if current_user.role == "USER":
        raise InsufficientPermissionsError("Not enough permissions")
    elif current_user.role != "SUPERUSER":
        if target_quote.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Can't delete sent quotes
    if target_quote.status in ["SENT", "RESPONDED"]:
        raise ValidationError("Cannot delete quotes that have been sent")
    
    await quote.remove(db=db, id=quote_id)
    return {"message": "Quote deleted successfully"}


@router.post("/{quote_id}/send")
async def send_quote(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    background_tasks: BackgroundTasks,
    quote_id: str,
    recipients: List[str],
    message: Optional[str] = None,
) -> Any:
    """
    Send quote to suppliers.
    """
    target_quote = await quote.get_with_items(db=db, id=quote_id)
    if not target_quote:
        raise EntityNotFoundError("Quote", quote_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_quote.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    if target_quote.status != "DRAFT":
        raise ValidationError("Only draft quotes can be sent")
    
    if not recipients:
        raise ValidationError("At least one recipient is required")
    
    # Update quote status
    from datetime import datetime
    await quote.update(
        db=db,
        db_obj=target_quote,
        obj_in=QuoteUpdate(
            status="SENT",
            sent_at=datetime.utcnow(),
            recipients=recipients
        )
    )
    
    # Send emails in background
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_quote_to_suppliers,
        quote=target_quote,
        recipients=recipients,
        message=message
    )
    
    return {"message": "Quote sent successfully"}


@router.get("/{quote_id}/responses")
async def get_quote_responses(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    quote_id: str,
) -> Any:
    """
    Get responses for a quote.
    """
    target_quote = await quote.get(db=db, id=quote_id)
    if not target_quote:
        raise EntityNotFoundError("Quote", quote_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_quote.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # This would return responses from a separate responses table
    # For now, return quote data with response status
    return {
        "quote_id": quote_id,
        "status": target_quote.status,
        "sent_at": target_quote.sent_at,
        "responded_at": target_quote.responded_at,
        "responses": target_quote.responses or [],
    }


@router.get("/pending/company")
async def get_pending_quotes(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get pending quotes for current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    pending_quotes = await quote.get_pending_quotes(
        db=db,
        company_id=current_user.company_id
    )
    
    return {"data": pending_quotes, "count": len(pending_quotes)}


@router.get("/sent/recent")
async def get_recent_sent_quotes(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    days: int = Query(30, ge=1, le=365),
) -> Any:
    """
    Get recently sent quotes.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    sent_quotes = await quote.get_sent_quotes(
        db=db,
        company_id=current_user.company_id,
        days=days
    )
    
    return {"data": sent_quotes, "count": len(sent_quotes)}


@router.get("/stats/company")
async def get_quote_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get quote statistics for current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    stats = await quote.get_stats(db=db, company_id=current_user.company_id)
    return stats
