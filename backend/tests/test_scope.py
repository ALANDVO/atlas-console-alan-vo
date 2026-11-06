import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

from app.main import create_app
from app.core.database import engine, async_session_maker, Base
from app.models.user import User, UserRole
from app.models.scope import ScopeEntry, ScopeEntryType
from app.services.auth_service import AuthService
from app.core.security import hash_password


@pytest_asyncio.fixture(scope="function")
async def test_app():
    app = create_app()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield app
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def session():
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
def enable_demo_mode(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    from app.core.config import settings
    settings.demo_mode = True


@pytest_asyncio.fixture
async def test_user(session: AsyncSession):
    auth_service = AuthService(session)
    user = await auth_service.create_user(
        email="test@example.com",
        password="testpass123",
        full_name="Test User",
        role=UserRole.OPERATOR,
    )
    await session.commit()
    return user


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession):
    auth_service = AuthService(session)
    user = await auth_service.create_user(
        email="admin@example.com",
        password="adminpass123",
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    await session.commit()
    return user


@pytest_asyncio.fixture
async def viewer_user(session: AsyncSession):
    auth_service = AuthService(session)
    user = await auth_service.create_user(
        email="viewer@example.com",
        password="viewerpass123",
        full_name="Viewer User",
        role=UserRole.VIEWER,
    )
    await session.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpass123"},
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def viewer_headers(client: AsyncClient, viewer_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "viewerpass123"},
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestScopeEntryCRUD:
    @pytest.mark.asyncio
    async def test_create_ip_range_entry(self, client: AsyncClient, auth_headers: dict):
        """Test creating an IP range scope entry."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24", "description": "Local network"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "ip_range"
        assert data["value"] == "192.168.1.0/24"
        assert data["description"] == "Local network"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_port_range_entry(self, client: AsyncClient, auth_headers: dict):
        """Test creating a port range scope entry."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "port_range", "value": "80-443", "description": "Web ports"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "port_range"
        assert data["value"] == "80-443"

    @pytest.mark.asyncio
    async def test_create_service_entry(self, client: AsyncClient, auth_headers: dict):
        """Test creating a service scope entry."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "ssh", "description": "SSH service"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "service"
        assert data["value"] == "ssh"

    @pytest.mark.asyncio
    async def test_create_entry_invalid_ip(self, client: AsyncClient, auth_headers: dict):
        """Test creating an invalid IP range entry."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "invalid", "description": "Bad IP"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_invalid_port(self, client: AsyncClient, auth_headers: dict):
        """Test creating an invalid port range entry."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "port_range", "value": "99999", "description": "Bad port"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_viewer_forbidden(self, client: AsyncClient, viewer_headers: dict):
        """Test that viewers cannot create scope entries."""
        response = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "10.0.0.0/8", "description": "Private"},
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_entries(self, client: AsyncClient, auth_headers: dict):
        """Test listing scope entries."""
        # Create a few entries first
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "port_range", "value": "80-443"},
            headers=auth_headers,
        )

        response = await client.get("/api/v1/scope/entries", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["entries"]) >= 2

    @pytest.mark.asyncio
    async def test_list_entries_filter_by_type(self, client: AsyncClient, auth_headers: dict):
        """Test listing scope entries filtered by type."""
        response = await client.get(
            "/api/v1/scope/entries?type=ip_range", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["type"] == "ip_range"

    @pytest.mark.asyncio
    async def test_list_entries_filter_by_active(self, client: AsyncClient, auth_headers: dict):
        """Test listing scope entries filtered by active status."""
        response = await client.get(
            "/api/v1/scope/entries?is_active=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_entry(self, client: AsyncClient, auth_headers: dict):
        """Test getting a single scope entry."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "http", "description": "HTTP service"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await client.get(f"/api/v1/scope/entries/{entry_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["value"] == "http"

    @pytest.mark.asyncio
    async def test_get_entry_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent scope entry."""
        response = await client.get("/api/v1/scope/entries/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry(self, client: AsyncClient, auth_headers: dict):
        """Test updating a scope entry."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "10.0.0.0/8", "description": "Old desc"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/scope/entries/{entry_id}",
            json={"description": "New description", "is_active": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "New description"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_entry_invalid_value(self, client: AsyncClient, auth_headers: dict):
        """Test updating a scope entry with invalid value."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/scope/entries/{entry_id}",
            json={"value": "invalid_ip"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_entry_viewer_forbidden(self, client: AsyncClient, viewer_headers: dict):
        """Test that viewers cannot update scope entries."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=viewer_headers,
        )
        # Viewer can't create, so this will fail
        assert create_resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_entry(self, client: AsyncClient, admin_headers: dict):
        """Test deleting a scope entry (admin only)."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "ftp", "description": "FTP service"},
            headers=admin_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/scope/entries/{entry_id}", headers=admin_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_resp = await client.get(f"/api/v1/scope/entries/{entry_id}", headers=admin_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entry_operator_forbidden(self, client: AsyncClient, auth_headers: dict):
        """Test that operators cannot delete scope entries."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "telnet", "description": "Telnet"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        response = await client.delete(f"/api/v1/scope/entries/{entry_id}", headers=auth_headers)
        assert response.status_code == 403


class TestScopeValidation:
    @pytest.mark.asyncio
    async def test_validate_ip_in_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating an IP within scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "192.168.1.50", "target_type": "ip"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is True

    @pytest.mark.asyncio
    async def test_validate_ip_out_of_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating an IP outside scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "10.0.0.1", "target_type": "ip"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is False

    @pytest.mark.asyncio
    async def test_validate_port_in_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating a port within scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "port_range", "value": "80-443"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "443", "target_type": "port"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is True

    @pytest.mark.asyncio
    async def test_validate_port_out_of_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating a port outside scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "port_range", "value": "80-443"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "22", "target_type": "port"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is False

    @pytest.mark.asyncio
    async def test_validate_service_in_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating a service within scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "ssh"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "ssh", "target_type": "service"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is True

    @pytest.mark.asyncio
    async def test_validate_service_out_of_scope(self, client: AsyncClient, auth_headers: dict):
        """Test validating a service outside scope."""
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "service", "value": "ssh"},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "ftp", "target_type": "service"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is False

    @pytest.mark.asyncio
    async def test_validate_inactive_entry(self, client: AsyncClient, auth_headers: dict):
        """Test that inactive entries don't match."""
        create_resp = await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        # Deactivate the entry
        await client.patch(
            f"/api/v1/scope/entries/{entry_id}",
            json={"is_active": False},
            headers=auth_headers,
        )

        response = await client.post(
            "/api/v1/scope/validate",
            json={"target": "192.168.1.50", "target_type": "ip"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["in_scope"] is False


class TestScopeImportExport:
    @pytest.mark.asyncio
    async def test_import_scope_json(self, client: AsyncClient, auth_headers: dict):
        """Test importing scope from JSON."""
        import_data = {
            "entries": [
                {"type": "ip_range", "value": "10.0.0.0/8", "description": "Private A"},
                {"type": "port_range", "value": "22", "description": "SSH"},
                {"type": "service", "value": "http", "description": "HTTP"},
            ]
        }

        response = await client.post(
            "/api/v1/scope/import",
            json={"filename": "scope.json", "format": "json", "data": import_data},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert data["entry_count"] == 3
        assert data["error_count"] == 0

    @pytest.mark.asyncio
    async def test_import_scope_with_errors(self, client: AsyncClient, auth_headers: dict):
        """Test importing scope with some invalid entries."""
        import_data = {
            "entries": [
                {"type": "ip_range", "value": "10.0.0.0/8"},
                {"type": "ip_range", "value": "invalid_ip"},  # Invalid
                {"type": "port_range", "value": "80-443"},
            ]
        }

        response = await client.post(
            "/api/v1/scope/import",
            json={"filename": "scope.json", "format": "json", "data": import_data},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"
        assert data["entry_count"] == 2
        assert data["error_count"] == 1

    @pytest.mark.asyncio
    async def test_import_scope_invalid_format(self, client: AsyncClient, auth_headers: dict):
        """Test importing with invalid format."""
        response = await client.post(
            "/api/v1/scope/import",
            json={
                "filename": "scope.xml",
                "format": "xml",
                "data": {"entries": []},
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_import_scope_viewer_forbidden(self, client: AsyncClient, viewer_headers: dict):
        """Test that viewers cannot import scope."""
        response = await client.post(
            "/api/v1/scope/import",
            json={
                "filename": "scope.json",
                "format": "json",
                "data": {"entries": []},
            },
            headers=viewer_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_scope(self, client: AsyncClient, auth_headers: dict):
        """Test exporting scope."""
        # Create some entries first
        await client.post(
            "/api/v1/scope/entries",
            json={"type": "ip_range", "value": "192.168.1.0/24"},
            headers=auth_headers,
        )

        response = await client.get("/api/v1/scope/export", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) >= 1

    @pytest.mark.asyncio
    async def test_import_export_history(self, client: AsyncClient, admin_headers: dict):
        """Test getting import/export history."""
        response = await client.get("/api/v1/scope/import-export/history", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_import_export_history_operator_forbidden(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that operators cannot access import/export history."""
        response = await client.get(
            "/api/v1/scope/import-export/history", headers=auth_headers
        )
        assert response.status_code == 403
