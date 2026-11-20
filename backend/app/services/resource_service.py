from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.resource import Resource, ResourceType, ResourceStatus
from app.models.user import User

logger = structlog.get_logger()


class ResourceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        path: Optional[str] = None,
        size: int = 0,
        mime_type: Optional[str] = None,
        tags: Optional[str] = None,
        description: Optional[str] = None,
        status: ResourceStatus = ResourceStatus.ACTIVE,
        created_by: int = 1,
    ) -> Resource:
        """Create a new resource."""
        resource = Resource(
            name=name,
            type=resource_type,
            path=path,
            size=size,
            mime_type=mime_type,
            tags=tags,
            description=description,
            status=status,
            created_by=created_by,
        )
        self.session.add(resource)
        # Use commit instead of flush for SQLite in-memory compatibility
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def get_resource(self, resource_id: int) -> Optional[Resource]:
        """Get a resource by ID."""
        result = await self.session.get(Resource, resource_id)
        return result

    async def list_resources(
        self,
        page: int = 1,
        page_size: int = 20,
        resource_type: Optional[ResourceType] = None,
        status: Optional[ResourceStatus] = None,
        search: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Tuple[List[Resource], int]:
        """List resources with pagination and filters.

        Returns (resources_list, total_count) for pagination.
        """
        query = select(Resource)
        count_query = select(func.count()).select_from(Resource)

        # Apply filters
        if resource_type is not None:
            query = query.where(Resource.type == resource_type)
            count_query = count_query.where(Resource.type == resource_type)

        if status is not None:
            query = query.where(Resource.status == status)
            count_query = count_query.where(Resource.status == status)

        if search is not None:
            search_filter = or_(
                Resource.name.ilike(f"%{search}%"),
                Resource.description.ilike(f"%{search}%") if Resource.description is not None else False,
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if tags is not None:
            query = query.where(Resource.tags.ilike(f"%{tags}%"))
            count_query = count_query.where(Resource.tags.ilike(f"%{tags}%"))

        # Get total count first
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        resources = result.scalars().unique().all()

        return list(resources), total

    async def update_resource(
        self,
        resource_id: int,
        name: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
        mime_type: Optional[str] = None,
        tags: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ResourceStatus] = None,
    ) -> Optional[Resource]:
        """Update a resource."""
        resource = await self.get_resource(resource_id)
        if resource is None:
            return None

        if name is not None:
            resource.name = name
        if path is not None:
            resource.path = path
        if size is not None:
            resource.size = size
        if mime_type is not None:
            resource.mime_type = mime_type
        if tags is not None:
            resource.tags = tags
        if description is not None:
            resource.description = description
        if status is not None:
            resource.status = status

        self.session.add(resource)
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def delete_resource(self, resource_id: int) -> bool:
        """Delete a resource."""
        resource = await self.get_resource(resource_id)
        if resource is None:
            return False

        await self.session.delete(resource)
        await self.session.commit()
        return True

    async def search_resources(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Resource], int]:
        """Search resources by name or description."""
        return await self.list_resources(
            page=page,
            page_size=page_size,
            search=query,
        )
