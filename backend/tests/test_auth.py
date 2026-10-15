import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio

from app.main import create_app
from app.core.database import engine, async_session_maker, Base
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.core.security import hash_password, verify_password


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


@pytest_asyncio.fixture
async def test_user(session: AsyncSession):
    auth_service = AuthService(session)
    user = await auth_service.create_user(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User",
        role=UserRole.OPERATOR,
    )
    return user


class TestAuth:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_api_info(self, client):
        resp = await client.get("/api/v1/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_login_disabled_without_demo_mode(self, client):
        # Default config has demo_mode=False
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_me(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_dashboard_unauthenticated(self, client):
        resp = await client.get("/api/v1/dashboard")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_password_hashing(self, client, session: AsyncSession):
        auth_service = AuthService(session)
        user = await auth_service.create_user(
            email="hash@example.com",
            password="securepassword",
            role=UserRole.VIEWER,
        )
        assert user.hashed_password != "securepassword"
        assert user.hashed_password.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_verify_password(self, client, session: AsyncSession):
        auth_service = AuthService(session)
        user = await auth_service.create_user(
            email="verify@example.com",
            password="verifyme",
            role=UserRole.VIEWER,
        )
        assert auth_service.verify_password("verifyme", user.hashed_password) is True
        assert auth_service.verify_password("wrong", user.hashed_password) is False


class TestAuthWithDemoMode:
    @pytest.fixture(autouse=True)
    def enable_demo_mode(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        # Need to reload settings
        from app.core.config import settings
        settings.demo_mode = True

    @pytest.mark.asyncio
    async def test_demo_token_endpoint(self, client, session: AsyncSession):
        resp = await client.post("/api/v1/auth/demo/token")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_demo_login(self, client, session: AsyncSession):
        # Ensure demo user exists
        await client.post("/api/v1/auth/demo/token")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@atlas.example", "password": "demo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client, session: AsyncSession):
        # Ensure demo user exists
        await client.post("/api/v1/auth/demo/token")
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@atlas.example", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticated_me_with_demo_token(self, client, session: AsyncSession):
        # Get token
        resp = await client.post("/api/v1/auth/demo/token")
        token = resp.json()["access_token"]

        # Use token
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "demo@atlas.example"
        assert data["role"] == "operator"

    @pytest.mark.asyncio
    async def test_dashboard_with_demo_token(self, client, session: AsyncSession):
        resp = await client.post("/api/v1/auth/demo/token")
        token = resp.json()["access_token"]

        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "recent_activity" in data
        assert "user" in data

    @pytest.mark.asyncio
    async def test_refresh_token(self, client, session: AsyncSession):
        resp = await client.post("/api/v1/auth/demo/token")
        refresh_token = resp.json()["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data


class TestRoleAuthorization:
    @pytest.fixture(autouse=True)
    def enable_demo_mode(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "true")
        from app.core.config import settings
        settings.demo_mode = True

    @pytest.mark.asyncio
    async def test_viewer_can_access_dashboard(self, client, session: AsyncSession):
        auth_service = AuthService(session)
        user = await auth_service.create_user(
            email="viewer@example.com",
            password="viewerpass",
            role=UserRole.VIEWER,
        )
        tokens = auth_service.create_tokens(user)
        token = tokens["access_token"]

        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_can_access_dashboard(self, client, session: AsyncSession):
        auth_service = AuthService(session)
        user = await auth_service.create_user(
            email="operator@example.com",
            password="operatorpass",
            role=UserRole.OPERATOR,
        )
        tokens = auth_service.create_tokens(user)
        token = tokens["access_token"]

        resp = await client.get(
            "/api/v1/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200