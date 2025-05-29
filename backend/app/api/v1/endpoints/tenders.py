"""
Tender management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_tender import tender
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityNotFoundError,
    InsufficientPermissionsError,
    ValidationError,
)
from app.schemas.tender import (
    TenderCreate,
    TenderInDB,
    TenderPublic,
    TenderUpdate,
    TendersPublic,
)
from app.services.file_service import FileService
from app.services.ai_service import AIService

router = APIRouter()


@router.get("/", response_model=TendersPublic)
async def read_tenders(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
) -> Any:
    """
    Retrieve tenders from the current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    tenders_data = await tender.get_multi_with_filters(
        db=db,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
        search=search,
        status=status,
        created_by=created_by,
    )
    
    return TendersPublic(
        data=tenders_data["data"],
        count=tenders_data["count"]
    )


@router.post("/", response_model=TenderPublic)
async def create_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_in: TenderCreate,
) -> Any:
    """
    Create new tender.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Set company_id and created_by
    tender_in.company_id = current_user.company_id
    tender_in.created_by = current_user.id
    
    new_tender = await tender.create(db=db, obj_in=tender_in)
    return new_tender


@router.post("/upload", response_model=TenderPublic)
async def upload_tender_document(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Any:
    """
    Upload tender document and start AI processing.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Validate file type
    allowed_types = ["application/pdf", "application/msword", 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise ValidationError("Only PDF and Word documents are allowed")
    
    # Save file
    file_service = FileService()
    file_path = await file_service.save_tender_file(
        file=file,
        company_id=current_user.company_id,
        user_id=current_user.id
    )
    
    # Create tender record
    tender_data = TenderCreate(
        title=title or file.filename,
        description=description,
        document_url=file_path,
        status="UPLOADED",
        company_id=current_user.company_id,
        created_by=current_user.id,
    )
    
    new_tender = await tender.create(db=db, obj_in=tender_data)
    
    # Start AI processing in background
    ai_service = AIService()
    background_tasks.add_task(
        ai_service.process_tender_document,
        tender_id=new_tender.id,
        file_path=file_path,
        db=db
    )
    
    return new_tender


@router.get("/{tender_id}", response_model=TenderPublic)
async def read_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_id: str,
) -> Any:
    """
    Get tender by ID.
    """
    target_tender = await tender.get_with_items(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    return target_tender


@router.put("/{tender_id}", response_model=TenderPublic)
async def update_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_id: str,
    tender_in: TenderUpdate,
) -> Any:
    """
    Update tender.
    """
    target_tender = await tender.get(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    updated_tender = await tender.update(db=db, db_obj=target_tender, obj_in=tender_in)
    return updated_tender


@router.delete("/{tender_id}")
async def delete_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_id: str,
) -> Any:
    """
    Delete tender (soft delete).
    """
    target_tender = await tender.get(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    
    # Check permissions
    if current_user.role == "USER":
        raise InsufficientPermissionsError("Not enough permissions")
    elif current_user.role != "SUPERUSER":
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    await tender.remove(db=db, id=tender_id)
    return {"message": "Tender deleted successfully"}


@router.post("/{tender_id}/process")
async def reprocess_tender(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    background_tasks: BackgroundTasks,
    tender_id: str,
) -> Any:
    """
    Reprocess tender with AI.
    """
    target_tender = await tender.get(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    if not target_tender.document_url:
        raise ValidationError("Tender has no document to process")
    
    # Update status
    await tender.update(
        db=db,
        db_obj=target_tender,
        obj_in=TenderUpdate(status="PROCESSING")
    )
    
    # Start AI processing in background
    ai_service = AIService()
    background_tasks.add_task(
        ai_service.process_tender_document,
        tender_id=tender_id,
        file_path=target_tender.document_url,
        db=db
    )
    
    return {"message": "Tender processing started"}


@router.get("/{tender_id}/analysis")
async def get_tender_analysis(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    tender_id: str,
) -> Any:
    """
    Get tender AI analysis results.
    """
    target_tender = await tender.get_with_items(db=db, id=tender_id)
    if not target_tender:
        raise EntityNotFoundError("Tender", tender_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_tender.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    return {
        "tender_id": tender_id,
        "status": target_tender.status,
        "ai_analysis": target_tender.ai_analysis,
        "items": target_tender.items,
        "processed_at": target_tender.processed_at,
    }


@router.get("/stats/company")
async def get_tender_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get tender statistics for current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    stats = await tender.get_stats(db=db, company_id=current_user.company_id)
    return stats


@router.get("/recent/activity")
async def get_recent_tender_activity(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    days: int = Query(7, ge=1, le=90),
) -> Any:
    """
    Get recent tender activity.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    recent_tenders = await tender.get_recent_activity(
        db=db,
        company_id=current_user.company_id,
        days=days
    )
    
    return {"data": recent_tenders, "count": len(recent_tenders)}
