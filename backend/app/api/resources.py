from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from app.api.auth import get_current_user
from app.schemas.resource import ResourceCreate, ResourceUpdate, ResourceResponse, ResourceListResponse
from app.services.resource_service import ResourceService
from app.core.database import get_async_session
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.ext.asyncio import AsyncSession

logger = __import__("structlog").get_logger()

router = APIRouter(prefix="/resources", tags=["resources"])


# Dependency to get resource service
def get_resource_service(session: AsyncSession = Depends(get_async_session)) -> ResourceService:
    return ResourceService(session)


@router.post(
    "/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    resource_in: ResourceCreate,
    current_user: ... = Depends(get_current_user),
    resource_service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    """Create a new resource. Requires authentication."""
    resource = await resource_service.create_resource(
        name=resource_in.name,
        resource_type=resource_in.type,
        path=resource_in.path,
        size=resource_in.size,
        mime_type=resource_in.mime_type,
        tags=resource_in.tags,
        description=resource_in.description,
        status=resource_in.status,
        created_by=current_user.id,
    )
    return ResourceResponse.from_orm(resource)


@router.get(
    "/", response_model=ResourceListResponse,
)
async def list_resources(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    resource_type: Optional[ResourceType] = Query(None, description="Filter by type"),
    status: Optional[ResourceStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    tags: Optional[str] = Query(None, description="Filter by tags"),
    current_user: ... = Depends(get_current_user),
    resource_service: ResourceService = Depends(get_resource_service),
) -> ResourceListResponse:
    """List resources with pagination. Requires authentication."""
    resources, total = await resource_service.list_resources(
        page=page,
        page_size=page_size,
        resource_type=resource_type,
        status=status,
        search=search,
        tags=tags,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ResourceListResponse(
        resources=resources,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{resource_id}", response_model=ResourceResponse,
)
async def get_resource(
    resource_id: int,
    current_user: ... = Depends(get_current_user),
    resource_service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    """Get a resource by ID. Requires authentication."""
    resource = await resource_service.get_resource(resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found",
        )
    return ResourceResponse.from_orm(resource)


@router.patch(
    "/{resource_id}", response_model=ResourceResponse,
)
async def update_resource(
    resource_id: int,
    resource_in: ResourceUpdate,
    current_user: ... = Depends(get_current_user),
    resource_service: ResourceService = Depends(get_resource_service),
) -> ResourceResponse:
    """Update a resource. Requires authentication."""
    resource = await resource_service.update_resource(
        resource_id=resource_id,
        name=resource_in.name,
        path=resource_in.path,
        size=resource_in.size,
        mime_type=resource_in.mime_type,
        tags=resource_in.tags,
        description=resource_in.description,
        status=resource_in.status,
    )
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found",
        )
    return ResourceResponse.from_orm(resource)


@router.delete(
    "/{resource_id}", status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_resource(
    resource_id: int,
    current_user: ... = Depends(get_current_user),
    resource_service: ResourceService = Depends(get_resource_service),
) -> None:
    """Delete a resource. Requires authentication."""
    deleted = await resource_service.delete_resource(resource_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_id} not found",
        )
