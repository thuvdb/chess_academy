import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CenterBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    logo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    facebook_page_url: str | None = None
    subscription_plan: str = "free"


class CenterCreate(CenterBase):
    pass


class CenterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = None
    logo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    facebook_page_url: str | None = None
    subscription_plan: str | None = None


class CenterRead(CenterBase):
    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    branches_count: int = 0
    members_count: int = 0
    classes_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CenterCleanupResult(BaseModel):
    deleted_count: int
    message: str
