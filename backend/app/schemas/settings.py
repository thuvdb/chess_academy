"""
Schemas for Settings & Catalog Items.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ==================== Catalog Items ====================

class CatalogItemBase(BaseModel):
    catalog_type: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    order_index: int = 0
    is_active: bool = True


class CatalogItemCreate(CatalogItemBase):
    center_id: uuid.UUID | None = None


class CatalogItemUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    order_index: int | None = None
    is_active: bool | None = None


class CatalogItemRead(CatalogItemBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Settings ====================

class SettingBase(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str
    value_type: str = "string"
    description: str | None = None
    category: str = "general"
    is_overridable: bool = True


class SettingCreate(SettingBase):
    center_id: uuid.UUID | None = None


class SettingUpdate(BaseModel):
    value: str


class SettingRead(SettingBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
