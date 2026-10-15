from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.user import User, UserRole
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    exchange_code_for_tokens,
    get_userinfo,
    build_authorization_url,
    build_logout_url,
)
from app.core.config import settings

logger = structlog.get_logger()


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        user.last_login = datetime.now(timezone.utc)
        await self.session.commit()
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_oidc_sub(self, oidc_sub: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.oidc_sub == oidc_sub))
        return result.scalar_one_or_none()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)
    async def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        oidc_sub: Optional[str] = None,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            oidc_sub=oidc_sub,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    def create_tokens(self, user: User) -> dict:
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name,
                "roles": [user.role.value],
            }
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "type": "refresh"}
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def verify_access_token(self, token: str) -> Optional[dict]:
        token_data = decode_token(token)
        if not token_data:
            return None
        return {
            "user_id": int(token_data.sub),
            "email": token_data.email,
            "name": token_data.name,
            "roles": token_data.roles,
        }

    # OIDC methods
    def get_authorization_url(self, state: str, nonce: str, code_challenge: str) -> str:
        return build_authorization_url(state, nonce, code_challenge)

    async def handle_oidc_callback(
        self, code: str, code_verifier: str
    ) -> tuple[User, dict]:
        tokens = await exchange_code_for_tokens(code, code_verifier)
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        if not access_token:
            raise ValueError("No access token in OIDC response")

        userinfo = await get_userinfo(access_token)
        oidc_sub = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name") or userinfo.get("preferred_username")

        if not oidc_sub or not email:
            raise ValueError("Missing required claims from OIDC provider")

        user = await self.get_user_by_oidc_sub(oidc_sub)
        if not user:
            user = await self.get_user_by_email(email)
            if user:
                user.oidc_sub = oidc_sub
                await self.session.commit()
            else:
                user = await self.create_user(
                    email=email,
                    password="",  # No password for OIDC users
                    full_name=name,
                    oidc_sub=oidc_sub,
                )

        user.last_login = datetime.now(timezone.utc)
        await self.session.commit()

        app_tokens = self.create_tokens(user)
        return user, {**app_tokens, "id_token": id_token}

    def get_logout_url(self, id_token_hint: Optional[str] = None) -> str:
        return build_logout_url(id_token_hint, settings.frontend_url)

    async def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        token_data = decode_token(refresh_token)
        if not token_data or token_data.roles != ["refresh"]:
            return None
        user = await self.get_user_by_id(int(token_data.sub))
        if not user or not user.is_active:
            return None
        return self.create_tokens(user)