"""
CAMS Core Configuration — Pydantic Settings.
Loads from .env file and environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
import json

_INSECURE_DEFAULTS = {
    "change-me-in-production",
    "change-me-in-production-use-openssl-rand-hex-32",
    "cams_admin123",
    "cams_secret",
    "cams_password",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- App ---
    APP_NAME: str = "CAMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    API_PUBLIC_URL: str = "http://localhost:8000"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://cams:cams_secret@localhost:5432/chess_academy"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""

    # --- Stockfish ---
    STOCKFISH_PATH: str = "/usr/games/stockfish"

    # --- PayOS ---
    PAYOS_CLIENT_ID: str = ""
    PAYOS_API_KEY: str = ""
    PAYOS_CHECKSUM_KEY: str = ""
    
    # --- VietQR ---
    VIETQR_BANK_ID: str = "MB"
    VIETQR_ACCOUNT_NO: str = "1234567890"
    VIETQR_ACCOUNT_NAME: str = "CAMS CHESS ACADEMY"

    # --- Auth & Registration ---
    ALLOW_PUBLIC_REGISTER: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @model_validator(mode="after")
    def _reject_insecure_production(self) -> "Settings":
        """Outside DEBUG mode, refuse to start with default secrets or wildcard CORS."""
        if self.DEBUG:
            return self
        problems = []
        if self.JWT_SECRET_KEY in _INSECURE_DEFAULTS or len(self.JWT_SECRET_KEY) < 32:
            problems.append("JWT_SECRET_KEY must be a random value of at least 32 chars")
        if "*" in self.CORS_ORIGINS:
            problems.append("CORS_ORIGINS must list real domains, not '*'")
        if any(p in self.DATABASE_URL for p in _INSECURE_DEFAULTS):
            problems.append("DATABASE_URL must not contain a default password")
        if problems:
            raise ValueError("Insecure production configuration: " + "; ".join(problems))
        return self


settings = Settings()
