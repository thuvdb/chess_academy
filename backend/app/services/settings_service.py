"""
Settings & Catalogs Service — Sprint 5 / CAMS-0025
Handles dynamic settings resolution hierarchy and configurable catalog items.
"""

import json
import logging
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import assert_same_center, is_super_admin
from app.models.settings import CatalogItem, Setting
from app.models.user import User
from app.schemas.settings import CatalogItemCreate, CatalogItemUpdate

logger = logging.getLogger(__name__)


def cast_setting_value(value: str, value_type: str) -> Any:
    """Cast string setting value to target Python data type."""
    try:
        if value_type == "int":
            return int(value)
        if value_type == "float":
            return float(value)
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes", "t")
        if value_type == "json":
            return json.loads(value)
    except Exception as exc:
        logger.warning("Failed to cast setting value '%s' to %s: %s", value, value_type, exc)
    return value


# ==============================================================================
# Settings CRUD & Hierarchy Resolution
# ==============================================================================

async def get_setting(
    db: AsyncSession,
    key: str,
    center_id: Optional[uuid.UUID] = None,
    default: Any = None,
) -> Any:
    """
    Resolve setting with multi-tenant hierarchy:
    1. Center override (where key=key and center_id=center_id)
    2. System default (where key=key and center_id IS NULL)
    3. Default parameter fallback
    """
    if center_id:
        res = await db.execute(
            select(Setting).where(Setting.key == key, Setting.center_id == center_id)
        )
        center_setting = res.scalar_one_or_none()
        if center_setting:
            return cast_setting_value(center_setting.value, center_setting.value_type)

    # Fallback to system-level setting
    res = await db.execute(
        select(Setting).where(Setting.key == key, Setting.center_id.is_(None))
    )
    system_setting = res.scalar_one_or_none()
    if system_setting:
        return cast_setting_value(system_setting.value, system_setting.value_type)

    return default


async def list_settings(
    db: AsyncSession,
    current_user: User,
    category: Optional[str] = None,
) -> list[Setting]:
    """
    List all settings applicable to current user.
    - Super Admin: sees all system settings (center_id IS NULL).
    - Center Admin: sees system settings with their center overrides applied.
    """
    # Fetch system settings
    stmt_sys = select(Setting).where(Setting.center_id.is_(None))
    if category:
        stmt_sys = stmt_sys.where(Setting.category == category)
    res_sys = await db.execute(stmt_sys)
    sys_settings = {s.key: s for s in res_sys.scalars().all()}

    if is_super_admin(current_user):
        return list(sys_settings.values())

    # If center admin, fetch center overrides and merge
    if current_user.center_id:
        stmt_ctr = select(Setting).where(Setting.center_id == current_user.center_id)
        if category:
            stmt_ctr = stmt_ctr.where(Setting.category == category)
        res_ctr = await db.execute(stmt_ctr)
        for ctr_s in res_ctr.scalars().all():
            sys_settings[ctr_s.key] = ctr_s

    return list(sys_settings.values())


async def update_setting(
    db: AsyncSession,
    key: str,
    value: str,
    current_user: User,
) -> Setting:
    """
    Update a setting.
    - Super Admin updates system-level setting (center_id IS NULL).
    - Center Admin updates/overrides setting for their center if is_overridable=True.
    """
    if is_super_admin(current_user):
        res = await db.execute(
            select(Setting).where(Setting.key == key, Setting.center_id.is_(None))
        )
        setting = res.scalar_one_or_none()
        if not setting:
            setting = Setting(key=key, value=value, center_id=None)
            db.add(setting)
        else:
            setting.value = value
        await db.flush()
        await db.refresh(setting)
        return setting

    # Center Admin check
    if not current_user.center_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any center")

    # Check system setting definition to ensure it is overridable
    res_sys = await db.execute(
        select(Setting).where(Setting.key == key, Setting.center_id.is_(None))
    )
    sys_setting = res_sys.scalar_one_or_none()
    if sys_setting and not sys_setting.is_overridable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Setting '{key}' cannot be overridden at center level",
        )

    # Check existing center override
    res_ctr = await db.execute(
        select(Setting).where(Setting.key == key, Setting.center_id == current_user.center_id)
    )
    ctr_setting = res_ctr.scalar_one_or_none()
    if not ctr_setting:
        ctr_setting = Setting(
            key=key,
            value=value,
            value_type=sys_setting.value_type if sys_setting else "string",
            description=sys_setting.description if sys_setting else None,
            category=sys_setting.category if sys_setting else "general",
            is_overridable=True,
            center_id=current_user.center_id,
        )
        db.add(ctr_setting)
    else:
        ctr_setting.value = value

    await db.flush()
    await db.refresh(ctr_setting)
    return ctr_setting


# ==============================================================================
# Catalog Items CRUD
# ==============================================================================

async def list_catalog_items(
    db: AsyncSession,
    current_user: User,
    catalog_type: Optional[str] = None,
    active_only: bool = True,
) -> list[CatalogItem]:
    """
    List catalog items visible to user:
    System items (center_id IS NULL) + user's center items.
    """
    stmt = select(CatalogItem)

    if is_super_admin(current_user):
        # Super admin sees all, or can filter
        pass
    elif current_user.center_id:
        stmt = stmt.where(
            or_(
                CatalogItem.center_id == current_user.center_id,
                CatalogItem.center_id.is_(None),
            )
        )
    else:
        stmt = stmt.where(CatalogItem.center_id.is_(None))

    if catalog_type:
        stmt = stmt.where(CatalogItem.catalog_type == catalog_type)

    if active_only:
        stmt = stmt.where(CatalogItem.is_active == True)  # noqa: E712

    stmt = stmt.order_by(CatalogItem.catalog_type, CatalogItem.order_index, CatalogItem.created_at)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_catalog_item(
    db: AsyncSession,
    data: CatalogItemCreate,
    current_user: User,
) -> CatalogItem:
    """Create a new catalog item."""
    target_center_id = None
    if is_super_admin(current_user):
        target_center_id = data.center_id  # Can be None for system-wide
    else:
        target_center_id = current_user.center_id

    # Check duplicate code in same scope
    stmt = select(CatalogItem).where(
        CatalogItem.catalog_type == data.catalog_type,
        CatalogItem.code == data.code,
    )
    if target_center_id:
        stmt = stmt.where(CatalogItem.center_id == target_center_id)
    else:
        stmt = stmt.where(CatalogItem.center_id.is_(None))

    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Catalog item with code '{data.code}' already exists for this scope",
        )

    item = CatalogItem(
        center_id=target_center_id,
        catalog_type=data.catalog_type,
        code=data.code,
        label=data.label,
        order_index=data.order_index,
        is_active=data.is_active,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update_catalog_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    data: CatalogItemUpdate,
    current_user: User,
) -> CatalogItem:
    """Update catalog item label, order_index, or is_active."""
    item = await db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    # Center assertion: cross-center returns 404
    if item.center_id:
        assert_same_center(current_user, item.center_id, detail="Catalog item not found")
    else:
        # System-level catalog item can only be modified by super_admin
        if not is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can modify system-level catalog items",
            )

    if data.label is not None:
        item.label = data.label
    if data.order_index is not None:
        item.order_index = data.order_index
    if data.is_active is not None:
        item.is_active = data.is_active

    await db.flush()
    await db.refresh(item)
    return item


async def deactivate_catalog_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    current_user: User,
) -> CatalogItem:
    """Deactivate catalog item instead of deleting (per Spec v1.1 §6)."""
    item = await db.get(CatalogItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Catalog item not found")

    if item.center_id:
        assert_same_center(current_user, item.center_id, detail="Catalog item not found")
    else:
        if not is_super_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can deactivate system-level catalog items",
            )

    item.is_active = False
    await db.flush()
    await db.refresh(item)
    return item
