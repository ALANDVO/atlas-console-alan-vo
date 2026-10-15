from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import bcrypt
from pydantic import BaseModel
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TokenData(BaseModel):
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: list[str] = []
    exp: int
    iat: int
    iss: Optional[str] = None


def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit; truncate if needed
    password_bytes = password.encode("utf-8")[:72]
    # Use bcrypt directly to avoid passlib backend issues with bcrypt 5.0+
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "iat": now, "iss": settings.app_name})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "iat": now, "iss": settings.app_name, "type": "refresh", "roles": ["refresh"]})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return TokenData(**payload)
    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        return None


# OIDC / Keycloak integration
class OIDCConfig(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str
    end_session_endpoint: str


_oidc_config_cache: Optional[OIDCConfig] = None


async def fetch_oidc_config() -> OIDCConfig:
    global _oidc_config_cache
    if _oidc_config_cache:
        return _oidc_config_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.oidc_discovery_url)
        resp.raise_for_status()
        data = resp.json()
        _oidc_config_cache = OIDCConfig(**data)
        return _oidc_config_cache


async def exchange_code_for_tokens(code: str, code_verifier: str) -> Dict[str, Any]:
    oidc_config = await fetch_oidc_config()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            oidc_config.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_userinfo(access_token: str) -> Dict[str, Any]:
    oidc_config = await fetch_oidc_config()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            oidc_config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def build_authorization_url(state: str, nonce: str, code_challenge: str) -> str:
    oidc_config = OIDCConfig(
        issuer=settings.oidc_issuer_url,
        authorization_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/auth",
        token_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/token",
        jwks_uri=f"{settings.oidc_issuer_url}/protocol/openid-connect/certs",
        userinfo_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/userinfo",
        end_session_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/logout",
    )
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": settings.oidc_scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{oidc_config.authorization_endpoint}?{query}"


def build_logout_url(id_token_hint: Optional[str] = None, post_logout_redirect_uri: Optional[str] = None) -> str:
    oidc_config = OIDCConfig(
        issuer=settings.oidc_issuer_url,
        authorization_endpoint="",
        token_endpoint="",
        jwks_uri="",
        userinfo_endpoint="",
        end_session_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/logout",
    )
    params = {}
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    if post_logout_redirect_uri:
        params["post_logout_redirect_uri"] = post_logout_redirect_uri
    query = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
    return f"{oidc_config.end_session_endpoint}?{query}" if query else oidc_config.end_session_endpoint