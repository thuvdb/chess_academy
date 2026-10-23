"""
Unit & Integration Tests for Centers API (CAMS-0058):
  - CRUD operations on /api/centers
  - Role-based permissions (super_admin vs center_admin vs teacher)
  - Member / class deletion guard
  - Automated test centers cleanup
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
from app.models.center import Branch, Center
from app.models.user import User

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()

SUPER_ADMIN_ID = uuid.uuid4()
ADMIN_A_ID = uuid.uuid4()
TEACHER_A_ID = uuid.uuid4()

USER_SUPER_ADMIN = User(
    id=SUPER_ADMIN_ID,
    email="superadmin@cams.test",
    full_name="Super Admin",
    role=Role.SUPER_ADMIN.value,
    center_id=None,
    is_active=True,
    elo_rating=800,
)

USER_ADMIN_A = User(
    id=ADMIN_A_ID,
    email="admin_a@cams.test",
    full_name="Admin Center A",
    role=Role.CENTER_ADMIN.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)

USER_TEACHER_A = User(
    id=TEACHER_A_ID,
    email="teacher_a@cams.test",
    full_name="Teacher A",
    role=Role.TEACHER.value,
    center_id=CENTER_A,
    is_active=True,
    elo_rating=800,
)


class MockResult:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else ([items] if items else [])

    def scalars(self):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_list_centers_super_admin(async_client):
    center1 = Center(id=CENTER_A, name="Center A", subscription_plan="free")
    center2 = Center(id=CENTER_B, name="Center B", subscription_plan="premium")

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockResult([center1, center2]))
    mock_db.scalar = AsyncMock(return_value=0)

    app.dependency_overrides[get_current_user] = lambda: USER_SUPER_ADMIN
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = await async_client.get("/api/centers")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["name"] == "Center A"
        assert data[1]["name"] == "Center B"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_center_forbidden_for_teacher(async_client):
    app.dependency_overrides[get_current_user] = lambda: USER_TEACHER_A
    try:
        res = await async_client.post(
            "/api/centers",
            json={"name": "New Center", "address": "123 Street"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_center_forbidden_for_center_admin(async_client):
    app.dependency_overrides[get_current_user] = lambda: USER_ADMIN_A
    try:
        res = await async_client.post(
            "/api/centers",
            json={"name": "New Center", "address": "123 Street"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_center_super_admin_success(async_client):
    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=0)
    mock_db.add = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: USER_SUPER_ADMIN
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = await async_client.post(
            "/api/centers",
            json={
                "name": "Học Viện Mới",
                "address": "456 Phố Cờ Vua",
                "phone": "0987654321",
                "subscription_plan": "basic",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Học Viện Mới"
        assert data["address"] == "456 Phố Cờ Vua"
        assert data["subscription_plan"] == "basic"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_center_blocked_when_has_members(async_client):
    center = Center(id=CENTER_A, name="Center A")
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockResult(center))
    # mock members_count = 5, classes_count = 0
    mock_db.scalar = AsyncMock(side_effect=[5, 0])

    app.dependency_overrides[get_current_user] = lambda: USER_SUPER_ADMIN
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = await async_client.delete(f"/api/centers/{CENTER_A}")
        assert res.status_code == 400
        assert "Không thể xóa trung tâm đang có" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_center_success_when_empty(async_client):
    center = Center(id=CENTER_A, name="Empty Test Center")
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MockResult(center))
    mock_db.scalar = AsyncMock(side_effect=[0, 0])
    mock_db.scalars = AsyncMock(return_value=MockResult([]))
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: USER_SUPER_ADMIN
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        res = await async_client.delete(f"/api/centers/{CENTER_A}")
        assert res.status_code == 200
        assert res.json()["message"] == "Đã xóa trung tâm thành công"
    finally:
        app.dependency_overrides.clear()
