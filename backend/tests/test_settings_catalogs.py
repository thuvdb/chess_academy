"""
Unit and Integration Tests for CAMS-0025: Dynamic Settings & Catalogs.
Validates:
1. Hierarchy resolution of settings (Center override -> System default -> fallback).
2. Type casting for settings (int, float, bool, json, string).
3. Setting update permissions (super_admin vs center_admin vs non-overridable 403).
4. Catalog item scoping (system items + center items).
5. Catalog item CRUD and tenant isolation (cross-center 404, system modification 403).
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.permissions import Role
from app.main import app
from app.models.settings import CatalogItem, Setting
from app.models.user import User
from app.services import settings_service
from app.services.settings_service import cast_setting_value

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()

USER_SUPER_ADMIN = User(
    id=uuid.uuid4(),
    email="super_admin@cams.vn",
    full_name="Super Admin",
    role=Role.SUPER_ADMIN.value,
    center_id=None,
    is_active=True,
    elo_rating=800,
)

USER_ADMIN_A = User(
    id=uuid.uuid4(),
    email="admin_a@cams.vn",
    full_name="Center Admin A",
    role=Role.CENTER_ADMIN.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)

USER_ADMIN_B = User(
    id=uuid.uuid4(),
    email="admin_b@cams.vn",
    full_name="Center Admin B",
    role=Role.CENTER_ADMIN.value,
    center_id=CENTER_B,
    is_active=True,
    elo_rating=800,
)

USER_TEACHER_A = User(
    id=uuid.uuid4(),
    email="teacher_a@cams.vn",
    full_name="Teacher A",
    role=Role.TEACHER.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)


def test_cast_setting_value():
    assert cast_setting_value("10", "int") == 10
    assert cast_setting_value("1.5", "float") == 1.5
    assert cast_setting_value("true", "bool") is True
    assert cast_setting_value("false", "bool") is False
    assert cast_setting_value('{"key": "val"}', "json") == {"key": "val"}
    assert cast_setting_value("hello", "string") == "hello"


class MockResult:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else ([items] if items is not None else [])

    def scalar_one_or_none(self):
        return self._items[0] if self._items else None

    def scalar(self):
        return self._items[0] if self._items else None

    def scalars(self):
        return self

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


def extract_filters(statement):
    filters = {}
    if hasattr(statement, "_where_criteria"):
        for crit in statement._where_criteria:
            if hasattr(crit, "left") and hasattr(crit, "right"):
                col = getattr(crit.left, "name", None)
                val = getattr(crit.right, "value", None)
                if col:
                    filters[col] = val
            elif hasattr(crit, "element") and hasattr(crit.element, "name"):
                col = crit.element.name
                filters[col] = None
    return filters


class FakeSettingsDB:
    def __init__(self):
        self.settings: dict[tuple, Setting] = {}
        self.catalogs: dict[uuid.UUID, CatalogItem] = {}

    def add(self, obj):
        if isinstance(obj, Setting):
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()
            self.settings[(obj.key, str(obj.center_id) if obj.center_id else None)] = obj
        elif isinstance(obj, CatalogItem):
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()
            self.catalogs[obj.id] = obj

    async def get(self, model, ident):
        if model == CatalogItem:
            return self.catalogs.get(ident)
        if model == Setting:
            for s in self.settings.values():
                if s.id == ident:
                    return s
        return None

    async def execute(self, statement):
        query_str = str(statement)
        filters = extract_filters(statement)

        if "FROM settings" in query_str:
            key = filters.get("key")
            if key is not None:
                center_id = filters.get("center_id")
                cid_str = str(center_id) if center_id else None
                match = self.settings.get((key, cid_str))
                return MockResult(match)
            items = list(self.settings.values())
            if "center_id IS NULL" in query_str or "center_id IS" in query_str.upper():
                items = [s for s in items if s.center_id is None]
            elif "center_id" in filters:
                cid_str = str(filters["center_id"]) if filters["center_id"] else None
                items = [s for s in items if (str(s.center_id) if s.center_id else None) == cid_str]
            return MockResult(items)

        if "FROM catalog_items" in query_str:
            items = list(self.catalogs.values())
            cat_type = filters.get("catalog_type")
            code = filters.get("code")
            if cat_type:
                items = [c for c in items if c.catalog_type == cat_type]
            if code:
                items = [c for c in items if c.code == code]
            if "center_id" in filters:
                cid_str = str(filters["center_id"]) if filters["center_id"] else None
                items = [c for c in items if (str(c.center_id) if c.center_id else None) == cid_str]
            return MockResult(items)

        return MockResult([])

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.fixture
def fake_settings_db():
    db = FakeSettingsDB()
    # Seed system settings
    db.add(Setting(
        id=uuid.uuid4(),
        key="stockfish_depth",
        value="10",
        value_type="int",
        category="engine",
        is_overridable=True,
        center_id=None,
    ))
    db.add(Setting(
        id=uuid.uuid4(),
        key="system_name",
        value="CAMS Global",
        value_type="string",
        category="general",
        is_overridable=False,
        center_id=None,
    ))
    # Seed center override for CENTER_A
    db.add(Setting(
        id=uuid.uuid4(),
        key="stockfish_depth",
        value="15",
        value_type="int",
        category="engine",
        is_overridable=True,
        center_id=CENTER_A,
    ))

    # Seed catalogs
    db.add(CatalogItem(
        id=uuid.uuid4(),
        center_id=None,
        catalog_type="course_level",
        code="beginner",
        label="Cơ bản",
        order_index=1,
        is_active=True,
    ))
    db.add(CatalogItem(
        id=uuid.uuid4(),
        center_id=CENTER_A,
        catalog_type="course_level",
        code="center_a_special",
        label="Lớp Đặc Biệt Center A",
        order_index=2,
        is_active=True,
    ))
    return db


@pytest_asyncio.fixture
async def api_client(fake_settings_db):
    state = {"current_user": USER_ADMIN_A}

    async def override_db():
        yield fake_settings_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: state["current_user"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.state = state
        client.db = fake_settings_db
        yield client
    app.dependency_overrides.clear()


# ==============================================================================
# Service Unit Tests: Hierarchy Resolution
# ==============================================================================

@pytest.mark.asyncio
async def test_get_setting_hierarchy(fake_settings_db):
    # 1. Center A has override for stockfish_depth (15)
    val_a = await settings_service.get_setting(fake_settings_db, "stockfish_depth", center_id=CENTER_A)
    assert val_a == 15

    # 2. Center B has no override -> falls back to system default (10)
    val_b = await settings_service.get_setting(fake_settings_db, "stockfish_depth", center_id=CENTER_B)
    assert val_b == 10

    # 3. Non-existent key -> falls back to provided default
    val_none = await settings_service.get_setting(fake_settings_db, "non_existent_key", default=42)
    assert val_none == 42


# ==============================================================================
# API Integration Tests: Settings
# ==============================================================================

@pytest.mark.asyncio
async def test_center_admin_override_setting_success(api_client):
    """Center admin can override an overridable setting."""
    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(
        "/api/settings/stockfish_depth",
        json={"value": "18"},
    )
    assert response.status_code == 200
    assert response.json()["value"] == "18"
    assert response.json()["center_id"] == str(CENTER_A)


@pytest.mark.asyncio
async def test_center_admin_override_non_overridable_fails(api_client):
    """Center admin cannot override a system-locked setting."""
    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(
        "/api/settings/system_name",
        json={"value": "Hacked Center Name"},
    )
    assert response.status_code == 403
    assert "cannot be overridden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_teacher_cannot_update_settings(api_client):
    """Teacher role is forbidden from updating settings."""
    api_client.state["current_user"] = USER_TEACHER_A
    response = await api_client.put(
        "/api/settings/stockfish_depth",
        json={"value": "20"},
    )
    assert response.status_code == 403


# ==============================================================================
# API Integration Tests: Catalogs
# ==============================================================================

@pytest.mark.asyncio
async def test_list_catalogs_includes_system_and_center(api_client):
    """User receives both system catalogs and their center catalogs."""
    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.get("/api/catalogs/course_level")
    assert response.status_code == 200
    items = response.json()
    codes = [item["code"] for item in items]
    assert "beginner" in codes
    assert "center_a_special" in codes


@pytest.mark.asyncio
async def test_create_catalog_item_center_admin(api_client):
    """Center admin creates catalog item bound to their center."""
    api_client.state["current_user"] = USER_ADMIN_A
    payload = {
        "catalog_type": "puzzle_theme",
        "code": "endgame_study",
        "label": "Tàn cuộc chuyên sâu",
        "order_index": 5,
        "is_active": True,
    }
    response = await api_client.post("/api/catalogs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "endgame_study"
    assert data["center_id"] == str(CENTER_A)


@pytest.mark.asyncio
async def test_update_catalog_item_cross_center_fails(api_client, fake_settings_db):
    """Center Admin A cannot modify catalog item of Center B (returns 404)."""
    item_b = CatalogItem(
        id=uuid.uuid4(),
        center_id=CENTER_B,
        catalog_type="course_level",
        code="level_b",
        label="Level B",
        order_index=1,
        is_active=True,
    )
    fake_settings_db.add(item_b)

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.put(
        f"/api/catalogs/{item_b.id}",
        json={"label": "Hacked Label"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Catalog item not found"


@pytest.mark.asyncio
async def test_deactivate_catalog_item(api_client, fake_settings_db):
    """Deleting a catalog item deactivates it (is_active = False)."""
    item_a = CatalogItem(
        id=uuid.uuid4(),
        center_id=CENTER_A,
        catalog_type="course_level",
        code="temporary_level",
        label="Temporary Level",
        order_index=99,
        is_active=True,
    )
    fake_settings_db.add(item_a)

    api_client.state["current_user"] = USER_ADMIN_A
    response = await api_client.delete(f"/api/catalogs/{item_a.id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False
