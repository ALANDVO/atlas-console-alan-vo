from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from app.core.database import get_session
from app.services.auth_service import AuthService
from app.models.user import User, UserRole

logger = structlog.get_logger()

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    total_flows: int = 0
    active_flows: int = 0
    completed_flows: int = 0
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0


class RecentActivity(BaseModel):
    id: int
    type: str
    title: str
    description: str
    timestamp: str
    status: str


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_activity: list[RecentActivity]
    user: dict


def require_role(allowed_roles: list[UserRole]):
    async def role_checker(request: Request, session: AsyncSession = Depends(get_session)) -> User:
        access_token = request.cookies.get("access_token")
        if not access_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                access_token = auth_header[7:]

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        auth_service = AuthService(session)
        token_data = auth_service.verify_access_token(access_token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user = await auth_service.get_user_by_id(token_data["user_id"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if user.role not in allowed_roles and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return role_checker


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    request: Request,
    user: User = Depends(require_role([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    """Get dashboard data - requires authentication."""
    # Mock data for now - replace with real queries later
    stats = DashboardStats(
        total_flows=12,
        active_flows=3,
        completed_flows=8,
        total_findings=47,
        critical_findings=2,
        high_findings=8,
    )

    recent_activity = [
        RecentActivity(
            id=1,
            type="flow_started",
            title="Penetration Test - Web App",
            description="Started automated penetration test on target web application",
            timestamp="2024-01-15T10:30:00Z",
            status="running",
        ),
        RecentActivity(
            id=2,
            type="finding",
            title="SQL Injection Found",
            description="Critical SQL injection in login form",
            timestamp="2024-01-15T09:15:00Z",
            status="critical",
        ),
        RecentActivity(
            id=3,
            type="flow_completed",
            title="Network Scan Complete",
            description="Completed network reconnaissance scan",
            timestamp="2024-01-14T16:45:00Z",
            status="completed",
        ),
    ]

    return DashboardResponse(
        stats=stats,
        recent_activity=recent_activity,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
        },
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    request: Request,
    user: User = Depends(require_role([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
    session: AsyncSession = Depends(get_session),
):
    """Get dashboard statistics only."""
    return DashboardStats(
        total_flows=12,
        active_flows=3,
        completed_flows=8,
        total_findings=47,
        critical_findings=2,
        high_findings=8,
    )