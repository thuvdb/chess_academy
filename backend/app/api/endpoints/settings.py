"""
Settings and Catalogs API Endpoints — CAMS-0025.
Provides dynamic configuration and catalog item management.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role, require_roles
from app.models.user import User
from app.schemas.settings import (
    CatalogItemCreate,
    CatalogItemRead,
    CatalogItemUpdate,
    SettingRead,
    SettingUpdate,
)
from app.services import settings_service

settings_router = APIRouter()
catalogs_router = APIRouter()


# ==============================================================================
# Settings Endpoints
# ==============================================================================

@settings_router.get("", response_model=list[SettingRead])
async def list_settings(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
):
    """List configuration settings applicable to the caller."""
    return await settings_service.list_settings(db, current_user, category=category)


@settings_router.put("/{key}", response_model=SettingRead)
async def update_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
):
    """Update or override a configuration setting."""
    setting = await settings_service.update_setting(
        db, key=key, value=data.value, current_user=current_user
    )
    await db.commit()
    return setting


# ==============================================================================
# Catalogs Endpoints
# ==============================================================================

@catalogs_router.get("", response_model=list[CatalogItemRead])
async def list_catalogs(
    catalog_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List catalog items available to the caller (system items + center items)."""
    return await settings_service.list_catalog_items(
        db, current_user, catalog_type=catalog_type, active_only=active_only
    )


@catalogs_router.get("/{catalog_type}", response_model=list[CatalogItemRead])
async def get_catalog_by_type(
    catalog_type: str,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convenience endpoint to fetch items for a specific catalog type (e.g. course_level)."""
    return await settings_service.list_catalog_items(
        db, current_user, catalog_type=catalog_type, active_only=active_only
    )


@catalogs_router.post("", response_model=CatalogItemRead, status_code=status.HTTP_201_CREATED)
async def create_catalog_item(
    data: CatalogItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
):
    """Create a new catalog item."""
    item = await settings_service.create_catalog_item(db, data, current_user)
    await db.commit()
    return item


@catalogs_router.put("/{item_id}", response_model=CatalogItemRead)
async def update_catalog_item(
    item_id: uuid.UUID,
    data: CatalogItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
):
    """Update a catalog item label, sort order, or active status."""
    item = await settings_service.update_catalog_item(db, item_id, data, current_user)
    await db.commit()
    return item


@catalogs_router.delete("/{item_id}", response_model=CatalogItemRead)
async def delete_catalog_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(Role.SUPER_ADMIN, Role.CENTER_ADMIN)),
):
    """Deactivate a catalog item."""
    item = await settings_service.deactivate_catalog_item(db, item_id, current_user)
    await db.commit()
    return item
