import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.core.database import engine, async_session_maker, Base
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


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
async def operator_token(client, session: AsyncSession):
    auth_service = AuthService(session)
    # Use unique email to avoid conflicts
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    email = f"operator_{unique_id}@example.com"
    user = await auth_service.create_user(
        email=email,
        password="operatorpass",
        role=UserRole.OPERATOR,
    )
    tokens = auth_service.create_tokens(user)
    return tokens["access_token"]


@pytest_asyncio.fixture
async def viewer_token(client, session: AsyncSession):
    auth_service = AuthService(session)
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    email = f"viewer_{unique_id}@example.com"
    user = await auth_service.create_user(
        email=email,
        password="viewerpass",
        role=UserRole.VIEWER,
    )
    tokens = auth_service.create_tokens(user)
    return tokens["access_token"]


class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_stats_structure(self, client, operator_token):
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_flows" in data
        assert "active_flows" in data
        assert "completed_flows" in data
        assert "total_findings" in data
        assert "critical_findings" in data
        assert "high_findings" in data
        assert all(isinstance(v, int) for v in data.values())

    @pytest.mark.asyncio
    async def test_dashboard_full_response(self, client, operator_token):
        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "recent_activity" in data
        assert "user" in data
        assert isinstance(data["recent_activity"], list)
        assert len(data["recent_activity"]) > 0

        # Check activity structure
        activity = data["recent_activity"][0]
        assert "id" in activity
        assert "type" in activity
        assert "title" in activity
        assert "description" in activity
        assert "timestamp" in activity
        assert "status" in activity

    @pytest.mark.asyncio
    async def test_dashboard_user_info(self, client, operator_token, session: AsyncSession):
        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        user = data["user"]
        assert "id" in user
        assert "email" in user
        assert "full_name" in user
        assert "role" in user
        assert user["role"] == "operator"

    @pytest.mark.asyncio
    async def test_dashboard_viewer_access(self, client, viewer_token):
        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(self, client):
        resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, client, operator_token):
        resp = await client.get(
            "/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_flows"] >= 0
        assert data["active_flows"] >= 0