from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import hashlib
import base64
import structlog

from app.core.database import get_session
from app.core.config import settings
from app.services.auth_service import AuthService
from app.models.user import User, UserRole

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


# PKCE helpers
def generate_code_verifier() -> str:
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


# Request/Response models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class OIDCLoginResponse(BaseModel):
    authorization_url: str
    state: str
    nonce: str
    code_verifier: str


class OIDCCallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: str

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )


# Demo user creation (for demo mode only)
async def ensure_demo_user(session: AsyncSession) -> User:
    auth_service = AuthService(session)
    user = await auth_service.get_user_by_email("demo@atlas.example")
    if not user:
        user = await auth_service.create_user(
            email="demo@atlas.example",
            password="demo",
            full_name="Demo User",
            role=UserRole.OPERATOR,
        )
        logger.info("demo_user_created", user_id=user.id)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate with email/password (demo mode only)."""
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password login disabled. Use OIDC/Keycloak.",
        )

    auth_service = AuthService(session)
    user = await auth_service.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    tokens = auth_service.create_tokens(user)
    # Set HttpOnly cookie for access token
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(session)
    tokens = await auth_service.refresh_access_token(request.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    return tokens


@router.post("/logout")
async def logout(response: Response):
    """Logout - clear cookies."""
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Get current authenticated user."""
    # Try cookie first, then Authorization header
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

    return UserResponse.from_user(user)


# OIDC routes
@router.get("/oidc/login", response_model=OIDCLoginResponse)
async def oidc_login():
    """Initiate OIDC login flow with PKCE."""
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC not enabled",
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)

    auth_service = AuthService(None)  # type: ignore
    auth_url = auth_service.get_authorization_url(state, nonce, code_challenge)

    return OIDCLoginResponse(
        authorization_url=auth_url,
        state=state,
        nonce=nonce,
        code_verifier=code_verifier,
    )


@router.post("/oidc/callback", response_model=TokenResponse)
async def oidc_callback(
    request: OIDCCallbackRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Handle OIDC callback with PKCE verification."""
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC not enabled",
        )

    auth_service = AuthService(session)
    try:
        user, tokens = await auth_service.handle_oidc_callback(
            request.code, request.code_verifier
        )
    except Exception as e:
        logger.error("oidc_callback_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC authentication failed",
        )

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return tokens


@router.get("/oidc/logout")
async def oidc_logout(request: Request, response: Response):
    """Initiate OIDC logout."""
    access_token = request.cookies.get("access_token")
    id_token_hint = None
    if access_token:
        auth_service = AuthService(None)  # type: ignore
        token_data = auth_service.verify_access_token(access_token)
        # We'd need to store id_token to pass as hint; skip for now

    auth_service = AuthService(None)  # type: ignore
    logout_url = auth_service.get_logout_url(id_token_hint)
    response.delete_cookie("access_token")
    return {"logout_url": logout_url}


# Demo mode: create demo user and return token
@router.post("/demo/token", response_model=TokenResponse)
async def demo_token(
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Get demo token (demo mode only)."""
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode not enabled",
        )

    user = await ensure_demo_user(session)
    auth_service = AuthService(session)
    tokens = auth_service.create_tokens(user)

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return tokens