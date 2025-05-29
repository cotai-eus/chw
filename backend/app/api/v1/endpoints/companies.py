"""
Company management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_company import company
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InsufficientPermissionsError,
)
from app.schemas.company import (
    CompanyCreate,
    CompanyInDB,
    CompanyPublic,
    CompanyUpdate,
    CompaniesPublic,
)

router = APIRouter()


@router.get("/", response_model=CompaniesPublic)
async def read_companies(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> Any:
    """
    Retrieve companies.
    Only SUPERUSER can access this endpoint.
    """
    companies_data = await company.get_multi_with_filters(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        is_active=is_active,
    )
    
    return CompaniesPublic(
        data=companies_data["data"],
        count=companies_data["count"]
    )


@router.post("/", response_model=CompanyPublic)
async def create_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
    company_in: CompanyCreate,
) -> Any:
    """
    Create new company.
    Only SUPERUSER can create companies.
    """
    # Check if company already exists
    existing_company = await company.get_by_name(db=db, name=company_in.name)
    if existing_company:
        raise EntityAlreadyExistsError("Company", "name", company_in.name)
    
    # Check CNPJ if provided
    if company_in.cnpj:
        existing_cnpj = await company.get_by_cnpj(db=db, cnpj=company_in.cnpj)
        if existing_cnpj:
            raise EntityAlreadyExistsError("Company", "cnpj", company_in.cnpj)
    
    new_company = await company.create(db=db, obj_in=company_in)
    return new_company


@router.get("/{company_id}", response_model=CompanyPublic)
async def read_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    company_id: str,
) -> Any:
    """
    Get company by ID.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        # Users and Admins can only see their own company
        if target_company.id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    return target_company


@router.put("/{company_id}", response_model=CompanyPublic)
async def update_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    company_id: str,
    company_in: CompanyUpdate,
) -> Any:
    """
    Update company.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    # Check permissions
    if current_user.role == "USER":
        raise InsufficientPermissionsError("Not enough permissions")
    elif current_user.role == "ADMIN":
        # Admins can only update their own company
        if target_company.id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    # SUPERUSER can update any company
    
    updated_company = await company.update(db=db, db_obj=target_company, obj_in=company_in)
    return updated_company


@router.delete("/{company_id}")
async def delete_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
    company_id: str,
) -> Any:
    """
    Delete company (soft delete).
    Only SUPERUSER can delete companies.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    # Soft delete
    await company.remove(db=db, id=company_id)
    return {"message": "Company deleted successfully"}


@router.post("/{company_id}/activate", response_model=CompanyPublic)
async def activate_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
    company_id: str,
) -> Any:
    """
    Activate company.
    Only SUPERUSER can activate companies.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    updated_company = await company.update(
        db=db, 
        db_obj=target_company, 
        obj_in=CompanyUpdate(is_active=True)
    )
    return updated_company


@router.post("/{company_id}/deactivate", response_model=CompanyPublic)
async def deactivate_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
    company_id: str,
) -> Any:
    """
    Deactivate company.
    Only SUPERUSER can deactivate companies.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    updated_company = await company.update(
        db=db, 
        db_obj=target_company, 
        obj_in=CompanyUpdate(is_active=False)
    )
    return updated_company


@router.get("/me/company", response_model=CompanyInDB)
async def read_my_company(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user's company.
    """
    if not current_user.company_id:
        raise EntityNotFoundError("Company", "current user has no company")
    
    user_company = await company.get(db=db, id=current_user.company_id)
    if not user_company:
        raise EntityNotFoundError("Company", current_user.company_id)
    
    return user_company


@router.get("/{company_id}/stats")
async def get_company_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    company_id: str,
) -> Any:
    """
    Get company statistics.
    """
    target_company = await company.get(db=db, id=company_id)
    if not target_company:
        raise EntityNotFoundError("Company", company_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_company.id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    stats = await company.get_stats(db=db, company_id=company_id)
    return stats
