from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import structlog

from app.core.database import get_session
from app.services.scope_service import ScopeService
from app.models.scope import ScopeEntry, ScopeEntryType, ScopeImportExport
from app.models.user import User, UserRole
from app.api.auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/scope", tags=["scope"])


# Request/Response models
class ScopeEntryCreate(BaseModel):
    type: ScopeEntryType
    value: str
    description: Optional[str] = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        if not v or len(v) > 512:
            raise ValueError("Value must be 1-512 characters")
        return v


class ScopeEntryUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ScopeEntryResponse(BaseModel):
    id: int
    type: ScopeEntryType
    value: str
    description: Optional[str]
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScopeEntryListResponse(BaseModel):
    entries: List[ScopeEntryResponse]
    total: int
    skip: int
    limit: int


class ScopeValidateRequest(BaseModel):
    target: str
    target_type: str  # ip, port, service


class ScopeValidateResponse(BaseModel):
    in_scope: bool


class ScopeImportRequest(BaseModel):
    filename: str
    format: str  # json, yaml
    data: dict


class ScopeImportExportResponse(BaseModel):
    id: int
    filename: str
    format: str
    status: str
    entry_count: int
    error_count: int
    errors: Optional[str]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Role dependency
def require_operator_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or Admin role required",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


# CRUD endpoints
@router.post(
    "/entries",
    response_model=ScopeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scope_entry(
    entry_data: ScopeEntryCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_operator_or_admin),
):
    """Create a new scope entry. Requires Operator or Admin role."""
    service = ScopeService(session)
    try:
        entry = await service.create_entry(
            entry_type=entry_data.type,
            value=entry_data.value,
            description=entry_data.description,
            created_by=current_user.id,
        )
        await session.commit()
        return entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/entries", response_model=ScopeEntryListResponse)
async def list_scope_entries(
    entry_type: Optional[ScopeEntryType] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List scope entries with optional filters. Requires authentication."""
    service = ScopeService(session)
    entries, total = await service.list_entries(
        entry_type=entry_type, is_active=is_active, skip=skip, limit=limit
    )
    return {
        "entries": entries,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/entries/{entry_id}", response_model=ScopeEntryResponse)
async def get_scope_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a scope entry by ID. Requires authentication."""
    service = ScopeService(session)
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scope entry not found"
        )
    return entry


@router.patch("/entries/{entry_id}", response_model=ScopeEntryResponse)
async def update_scope_entry(
    entry_id: int,
    entry_data: ScopeEntryUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_operator_or_admin),
):
    """Update a scope entry. Requires Operator or Admin role."""
    service = ScopeService(session)
    try:
        entry = await service.update_entry(
            entry_id=entry_id,
            value=entry_data.value,
            description=entry_data.description,
            is_active=entry_data.is_active,
        )
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scope entry not found"
            )
        await session.commit()
        return entry
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Delete a scope entry. Requires Admin role."""
    service = ScopeService(session)
    deleted = await service.delete_entry(entry_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scope entry not found"
        )
    await session.commit()


# Validation endpoint
@router.post("/validate", response_model=ScopeValidateResponse)
async def validate_target(
    request: ScopeValidateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Validate if a target is within scope. Requires authentication."""
    service = ScopeService(session)
    in_scope = await service.validate_target(request.target, request.target_type)
    return {"in_scope": in_scope}


# Import/Export endpoints
@router.post(
    "/import",
    response_model=ScopeImportExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_scope(
    request: ScopeImportRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_operator_or_admin),
):
    """Import scope entries from JSON/YAML. Requires Operator or Admin role."""
    if request.format not in ["json", "yaml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'json' or 'yaml'",
        )

    service = ScopeService(session)
    import_record = await service.import_scope(
        filename=request.filename,
        format=request.format,
        data=request.data,
        created_by=current_user.id,
    )
    await session.commit()
    return import_record


@router.get("/export")
async def export_scope(
    format: str = Query("json", pattern="^(json|yaml)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Export all active scope entries. Requires authentication."""
    service = ScopeService(session)
    data = await service.export_scope(format, current_user.id)
    return data


@router.get("/import-export/history", response_model=list[ScopeImportExportResponse])
async def get_import_export_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Get import/export history. Requires Admin role."""
    service = ScopeService(session)
    records, _ = await service.get_import_export_history(skip=skip, limit=limit)
    return records
