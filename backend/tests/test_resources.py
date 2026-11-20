import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.core.database import Base, async_session_maker, engine
from app.services.resource_service import ResourceService


@pytest.fixture(scope="function", autouse=True)
async def setup_and_teardown_database():
    """Initialize database before each test and rollback after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Rollback any pending transactions
    async with async_session_maker() as session:
        await session.rollback()


@pytest.fixture(scope="function")
async def async_session():
    """Create an async session for each test."""
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def resource_service(async_session):
    """Provide ResourceService instance."""
    return ResourceService(async_session)


class TestResourceListPagination:
    """Test paginated resource listing."""

    async def test_list_resources_pagination_basic(
        self, async_session, resource_service
    ):
        """Test that resources are created and can be listed."""
        # Create some test resources
        for i in range(3):
            resource = await resource_service.create_resource(
                name=f"Resource {i}",
                resource_type="file",
                path=f"/path/{i}",
                size=1024 * (i + 1),
                created_by=1,
            )
        
        # Test listing - verify resources exist
        resources, total = await resource_service.list_resources(
            page=1, page_size=10
        )
        assert total >= 3
        assert len(resources) >= 1

    async def test_list_resources_with_type_filter(
        self, async_session, resource_service
    ):
        """Test filtering resources by type."""
        # Create resources of different types
        await resource_service.create_resource(
            name="File 1", resource_type="file", created_by=1
        )
        await resource_service.create_resource(
            name="Dir 1", resource_type="directory", created_by=1
        )
        
        # Filter by file type
        resources, total = await resource_service.list_resources(
            page=1, page_size=10, resource_type="file"
        )
        assert total >= 1
        assert resources[0].type.value == "file"
        
        # Filter by directory type
        resources, total = await resource_service.list_resources(
            page=1, page_size=10, resource_type="directory"
        )
        assert total >= 1
        assert resources[0].type.value == "directory"

    async def test_list_resources_with_search(
        self, async_session, resource_service
    ):
        """Test searching resources."""
        # Create resources
        await resource_service.create_resource(
            name="Alpha Document", resource_type="note", description="First note", created_by=1
        )
        await resource_service.create_resource(
            name="Beta Document", resource_type="note", description="Second note", created_by=1
        )
        
        # Search by term
        resources, total = await resource_service.list_resources(
            page=1, page_size=10, search="Alpha"
        )
        assert total >= 1
        assert resources[0].name == "Alpha Document"
        
        resources, total = await resource_service.list_resources(
            page=1, page_size=10, search="note"
        )
        assert total >= 2


class TestResourceCRUD:
    """Test resource CRUD operations."""

    async def test_create_resource(self, async_session, resource_service):
        """Test creating a resource."""
        resource = await resource_service.create_resource(
            name="Test Resource",
            resource_type="file",
            path="/test/path",
            size=42,
            mime_type="text/plain",
            tags="tag1,tag2",
            description="A test resource",
            created_by=1,
        )
        assert resource.name == "Test Resource"
        assert resource.type.value == "file"
        assert resource.size == 42
        assert resource.mime_type == "text/plain"
        assert resource.tags == "tag1,tag2"
        assert resource.description == "A test resource"
        assert resource.status.value == "active"

    async def test_get_resource(self, async_session, resource_service):
        """Test getting a resource by ID."""
        created = await resource_service.create_resource(
            name="Get Test", resource_type="image", created_by=1
        )
        retrieved = await resource_service.get_resource(created.id)
        assert retrieved is not None
        assert retrieved.name == "Get Test"
        assert retrieved.type.value == "image"

    async def test_update_resource(self, async_session, resource_service):
        """Test updating a resource."""
        created = await resource_service.create_resource(
            name="Before", resource_type="file", created_by=1
        )
        updated = await resource_service.update_resource(
            resource_id=created.id,
            name="After",
            description="Updated description",
        )
        assert updated is not None
        assert updated.name == "After"
        assert updated.description == "Updated description"

    async def test_delete_resource(self, async_session, resource_service):
        """Test deleting a resource."""
        created = await resource_service.create_resource(
            name="To Delete", resource_type="file", created_by=1
        )
        deleted = await resource_service.delete_resource(created.id)
        assert deleted is True
        
        # Verify it's gone
        retrieved = await resource_service.get_resource(created.id)
        assert retrieved is None

    async def test_search_resources(self, async_session, resource_service):
        """Test resource search functionality."""
        await resource_service.create_resource(
            name="Search Me One", resource_type="note", created_by=1
        )
        await resource_service.create_resource(
            name="Search Me Two", resource_type="note", created_by=1
        )
        await resource_service.create_resource(
            name="Different", resource_type="file", created_by=1
        )
        
        # Search by term
        resources, total = await resource_service.search_resources(
            query="Search", page=1, page_size=10
        )
        assert total >= 2
        names = {r.name for r in resources}
        assert "Search Me One" in names
        assert "Search Me Two" in names
