"""
Pydantic Schemas for AI Settings and Providers Admin Management.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


class AIProviderBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: str = Field(..., pattern="^(gemini|openai_compatible)$")
    base_url: Optional[str] = Field(None, max_length=500)
    models: list[str] = Field(default_factory=list)
    enabled: bool = True


class AIProviderCreate(AIProviderBase):
    api_key: Optional[str] = Field(None, description="Plaintext API key to be encrypted")


class AIProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    type: Optional[str] = Field(None, pattern="^(gemini|openai_compatible)$")
    base_url: Optional[str] = Field(None, max_length=500)
    models: Optional[list[str]] = None
    enabled: Optional[bool] = None
    api_key: Optional[str] = Field(None, description="New API key (omit or leave empty to keep existing)")


class AIProviderOut(AIProviderBase):
    id: uuid.UUID
    api_key_masked: str
    has_key: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AISettingsUpdate(BaseModel):
    default_provider_id: Optional[uuid.UUID] = None
    default_model: Optional[str] = Field(None, min_length=1, max_length=100)
    fallback_provider_id: Optional[uuid.UUID] = None
    fallback_model: Optional[str] = Field(None, max_length=100)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(None, ge=100, le=8192)
    request_timeout_seconds: Optional[int] = Field(None, ge=5, le=120)
    max_retries: Optional[int] = Field(None, ge=0, le=5)


class AISettingsOut(BaseModel):
    id: uuid.UUID
    default_provider_id: Optional[uuid.UUID]
    default_model: str
    fallback_provider_id: Optional[uuid.UUID]
    fallback_model: Optional[str]
    temperature: float
    max_output_tokens: int
    request_timeout_seconds: int
    max_retries: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminAISettingsOverview(BaseModel):
    settings: AISettingsOut
    providers: list[AIProviderOut]


class AIProviderTestResponse(BaseModel):
    success: bool
    latency_ms: int
    response: Optional[str] = None
    error: Optional[str] = None


class AIModelsResponse(BaseModel):
    models: list[str]
    source: str  # "remote" | "stored"
    error: Optional[str] = None


class AISettingsAuditOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}

