"""
CAMS Core Configuration — Pydantic Settings.
Loads from .env file and environment variables.
"""

import json
from pathlib import Path
from typing import Any, Literal, Union

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULTS = {
    "change-me-in-production",
    "change-me-in-production-use-openssl-rand-hex-32",
    "cams_admin123",
    "cams_secret",
    "cams_password",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=True,
    )

    # --- Environment & App ---
    APP_ENV: Literal["local", "uat", "production"] = "local"
    APP_NAME: str = "CAMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- API & CORS ---
    API_PUBLIC_URL: str = "http://localhost:8000"
    BACKEND_CORS_ORIGINS: Union[str, list[str]] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            val = v.strip()
            if not val:
                return []
            if val.startswith("[") and val.endswith("]"):
                try:
                    items = json.loads(val)
                    return [str(x).strip() for x in items if str(x).strip()]
                except Exception:
                    inner = val[1:-1].strip()
                    return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
            return [x.strip() for x in val.split(",") if x.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return self.BACKEND_CORS_ORIGINS if isinstance(self.BACKEND_CORS_ORIGINS, list) else []

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://cams:cams_secret@localhost:5432/chess_academy"

    # --- Redis & Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- JWT & Security ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=1440,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"),
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS", "JWT_REFRESH_TOKEN_EXPIRE_DAYS"),
    )

    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def JWT_REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS

    # --- Storage & Uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # --- Engine & AI Models ---
    STOCKFISH_PATH: str = "/usr/games/stockfish"
    STOCKFISH_DEPTH: int = 15
    YOLO_MODEL_PATH: str = "models/chess_yolov8s.pt"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_TUTOR_PROVIDER: str = "gemini"
    AI_TUTOR_RATE_LIMIT_PER_MINUTE: int = 10
    AI_TUTOR_RATE_LIMIT_PER_DAY: int = 100
    AI_TUTOR_CACHE_TTL: int = 3600
    AI_TUTOR_HISTORY_LIMIT: int = 10
    AI_TUTOR_MAX_TOKENS: int = 1500

    # --- Seed & Defaults ---
    SEED_DEFAULT_PASSWORD: str = "Cams@2026!"
    DEFAULT_BRANCH_NAME: str = "Cơ sở Chính - Quận 1"

    # --- OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FACEBOOK_CLIENT_ID: str = ""
    FACEBOOK_CLIENT_SECRET: str = ""

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

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def normalize_app_env(cls, v: Any) -> str:
        if isinstance(v, str):
            env_val = v.strip().lower()
            if env_val in ("local", "uat", "production"):
                return env_val
        return "local"

    @model_validator(mode="after")
    def _validate_production_safety(self) -> "Settings":
        """In production environment, refuse to start with default secrets or wildcard CORS."""
        if self.APP_ENV == "production":
            problems = []
            if self.JWT_SECRET_KEY in _INSECURE_DEFAULTS or len(self.JWT_SECRET_KEY) < 32:
                problems.append(
                    "JWT_SECRET_KEY must not be a default/placeholder and must be at least 32 characters in production"
                )
            cors_list = self.BACKEND_CORS_ORIGINS if isinstance(self.BACKEND_CORS_ORIGINS, list) else []
            if any(origin == "*" for origin in cors_list):
                problems.append("BACKEND_CORS_ORIGINS must list explicit domains, not '*' in production")
            if any(p in self.DATABASE_URL for p in _INSECURE_DEFAULTS):
                problems.append("DATABASE_URL must not contain default credentials in production")
            if problems:
                raise ValueError("Insecure production configuration: " + "; ".join(problems))
        elif not self.DEBUG:
            # General non-debug check (e.g. UAT)
            if self.JWT_SECRET_KEY in _INSECURE_DEFAULTS or len(self.JWT_SECRET_KEY) < 32:
                # Can enforce or warn
                pass
        return self


settings = Settings()
