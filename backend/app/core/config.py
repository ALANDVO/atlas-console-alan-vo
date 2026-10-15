from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Atlas Console"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./atlas.db"

    # Security
    secret_key: str = Field(default="dev-secret-change-in-production-min-32-chars-long", min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OIDC / Keycloak
    oidc_enabled: bool = True
    oidc_issuer_url: str = "http://localhost:8080/realms/atlas"
    oidc_client_id: str = "atlas-console"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/callback"
    oidc_scopes: str = "openid profile email"

    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"

    # Demo mode (localhost only)
    demo_mode: bool = False

    @property
    def oidc_discovery_url(self) -> str:
        return f"{self.oidc_issuer_url.rstrip('/')}/.well-known/openid-configuration"

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]


settings = Settings()