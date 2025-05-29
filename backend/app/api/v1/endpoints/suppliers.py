"""
Supplier management endpoints.
"""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud.crud_supplier import supplier
from app.db.models.user import User
from app.exceptions.custom_exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InsufficientPermissionsError,
)
from app.schemas.supplier import (
    SupplierCreate,
    SupplierInDB,
    SupplierPublic,
    SupplierUpdate,
    SuppliersPublic,
)

router = APIRouter()


@router.get("/", response_model=SuppliersPublic)
async def read_suppliers(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
) -> Any:
    """
    Retrieve suppliers from the current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    suppliers_data = await supplier.get_multi_with_filters(
        db=db,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        is_active=is_active,
    )
    
    return SuppliersPublic(
        data=suppliers_data["data"],
        count=suppliers_data["count"]
    )


@router.post("/", response_model=SupplierPublic)
async def create_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    supplier_in: SupplierCreate,
) -> Any:
    """
    Create new supplier.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    # Check if supplier already exists by email
    if supplier_in.email:
        existing_supplier = await supplier.get_by_email(db=db, email=supplier_in.email)
        if existing_supplier and existing_supplier.company_id == current_user.company_id:
            raise EntityAlreadyExistsError("Supplier", "email", supplier_in.email)
    
    # Check if supplier already exists by CNPJ
    if supplier_in.cnpj:
        existing_cnpj = await supplier.get_by_cnpj(db=db, cnpj=supplier_in.cnpj)
        if existing_cnpj and existing_cnpj.company_id == current_user.company_id:
            raise EntityAlreadyExistsError("Supplier", "cnpj", supplier_in.cnpj)
    
    # Set company_id
    supplier_in.company_id = current_user.company_id
    
    new_supplier = await supplier.create(db=db, obj_in=supplier_in)
    return new_supplier


@router.get("/{supplier_id}", response_model=SupplierPublic)
async def read_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    supplier_id: str,
) -> Any:
    """
    Get supplier by ID.
    """
    target_supplier = await supplier.get(db=db, id=supplier_id)
    if not target_supplier:
        raise EntityNotFoundError("Supplier", supplier_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_supplier.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    return target_supplier


@router.put("/{supplier_id}", response_model=SupplierPublic)
async def update_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    supplier_id: str,
    supplier_in: SupplierUpdate,
) -> Any:
    """
    Update supplier.
    """
    target_supplier = await supplier.get(db=db, id=supplier_id)
    if not target_supplier:
        raise EntityNotFoundError("Supplier", supplier_id)
    
    # Check permissions
    if current_user.role != "SUPERUSER":
        if target_supplier.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    # Check email uniqueness if changed
    if supplier_in.email and supplier_in.email != target_supplier.email:
        existing_email = await supplier.get_by_email(db=db, email=supplier_in.email)
        if existing_email and existing_email.company_id == target_supplier.company_id:
            raise EntityAlreadyExistsError("Supplier", "email", supplier_in.email)
    
    # Check CNPJ uniqueness if changed
    if supplier_in.cnpj and supplier_in.cnpj != target_supplier.cnpj:
        existing_cnpj = await supplier.get_by_cnpj(db=db, cnpj=supplier_in.cnpj)
        if existing_cnpj and existing_cnpj.company_id == target_supplier.company_id:
            raise EntityAlreadyExistsError("Supplier", "cnpj", supplier_in.cnpj)
    
    updated_supplier = await supplier.update(db=db, db_obj=target_supplier, obj_in=supplier_in)
    return updated_supplier


@router.delete("/{supplier_id}")
async def delete_supplier(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    supplier_id: str,
) -> Any:
    """
    Delete supplier (soft delete).
    """
    target_supplier = await supplier.get(db=db, id=supplier_id)
    if not target_supplier:
        raise EntityNotFoundError("Supplier", supplier_id)
    
    # Check permissions
    if current_user.role == "USER":
        raise InsufficientPermissionsError("Not enough permissions")
    elif current_user.role != "SUPERUSER":
        if target_supplier.company_id != current_user.company_id:
            raise InsufficientPermissionsError("Not enough permissions")
    
    await supplier.remove(db=db, id=supplier_id)
    return {"message": "Supplier deleted successfully"}


@router.get("/search/by-products")
async def search_suppliers_by_products(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    keywords: str = Query(..., description="Comma-separated product keywords"),
) -> Any:
    """
    Search suppliers by products they offer.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    product_keywords = [k.strip() for k in keywords.split(",")]
    
    suppliers_list = await supplier.search_by_products(
        db=db,
        company_id=current_user.company_id,
        product_keywords=product_keywords,
    )
    
    return {"data": suppliers_list, "count": len(suppliers_list)}


@router.get("/filter/by-categories")
async def get_suppliers_by_categories(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    categories: str = Query(..., description="Comma-separated categories"),
) -> Any:
    """
    Get suppliers by categories.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    category_list = [c.strip() for c in categories.split(",")]
    
    suppliers_list = await supplier.get_by_categories(
        db=db,
        company_id=current_user.company_id,
        categories=category_list,
    )
    
    return {"data": suppliers_list, "count": len(suppliers_list)}


@router.get("/stats/company")
async def get_supplier_stats(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get supplier statistics for current user's company.
    """
    if not current_user.company_id:
        raise InsufficientPermissionsError("User must belong to a company")
    
    stats = await supplier.get_stats(db=db, company_id=current_user.company_id)
    return stats
