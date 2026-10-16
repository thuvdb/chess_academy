"""
Comprehensive Unit & Integration Tests for CAMS-0023:
  - RBAC core helpers in app/core/permissions.py
  - User provisioning endpoint POST /api/users
  - Tenant isolation and cross-center 404 assertion
  - Parent-student linkage and validation
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
from app.core.permissions import (
    Role,
    assert_owner_or_admin,
    assert_same_center,
    is_admin,
    is_center_admin,
    is_super_admin,
    require_roles,
    scope_query_to_center,
)
from app.main import app
from app.models.user import User

CENTER_A = uuid.uuid4()
CENTER_B = uuid.uuid4()


# --- Unit Tests: RBAC Helpers ---

def test_role_helpers():
    super_admin = SimpleNamespace(role=Role.SUPER_ADMIN.value, center_id=None)
    center_admin = SimpleNamespace(role=Role.CENTER_ADMIN.value, center_id=CENTER_A)
    legacy_admin = SimpleNamespace(role=Role.ADMIN.value, center_id=CENTER_A)
    teacher = SimpleNamespace(role=Role.TEACHER.value, center_id=CENTER_A)

    assert is_super_admin(super_admin) is True
    assert is_super_admin(center_admin) is False

    assert is_center_admin(center_admin) is True
    assert is_center_admin(legacy_admin) is True
    assert is_center_admin(teacher) is False

    assert is_admin(super_admin) is True
    assert is_admin(center_admin) is True
    assert is_admin(legacy_admin) is True
    assert is_admin(teacher) is False


def test_assert_same_center():
    super_admin = SimpleNamespace(role=Role.SUPER_ADMIN.value, center_id=None)
    user_a = SimpleNamespace(role=Role.CENTER_ADMIN.value, center_id=CENTER_A)

    # super_admin always passes
    assert_same_center(super_admin, CENTER_B)
    assert_same_center(super_admin, None)

    # Same center passes
    assert_same_center(user_a, CENTER_A)

    # Different center raises 404 NOT FOUND (never 403)
    with pytest.raises(HTTPException) as exc:
        assert_same_center(user_a, CENTER_B)
    assert exc.value.status_code == 404

    # None center raises 404
    with pytest.raises(HTTPException) as exc:
        assert_same_center(user_a, None)
    assert exc.value.status_code == 404


def test_assert_owner_or_admin():
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()

    owner = SimpleNamespace(id=owner_id, role=Role.TEACHER.value, center_id=CENTER_A)
    colleague = SimpleNamespace(id=other_id, role=Role.TEACHER.value, center_id=CENTER_A)
    admin_same_center = SimpleNamespace(id=other_id, role=Role.CENTER_ADMIN.value, center_id=CENTER_A)
    admin_diff_center = SimpleNamespace(id=other_id, role=Role.CENTER_ADMIN.value, center_id=CENTER_B)
    super_admin = SimpleNamespace(id=other_id, role=Role.SUPER_ADMIN.value, center_id=None)

    # 1. Owner can access
    assert_owner_or_admin(owner, owner_id, CENTER_A)

    # 2. Super admin can access anything
    assert_owner_or_admin(super_admin, owner_id, CENTER_A)
    assert_owner_or_admin(super_admin, owner_id, CENTER_B)

    # 3. Center admin of same center can access
    assert_owner_or_admin(admin_same_center, owner_id, CENTER_A)

    # 4. Center admin of different center gets 404
    with pytest.raises(HTTPException) as exc:
        assert_owner_or_admin(admin_diff_center, owner_id, CENTER_A)
    assert exc.value.status_code == 404

    # 5. Colleague in same center (neither owner nor admin) gets 403
    with pytest.raises(HTTPException) as exc:
        assert_owner_or_admin(colleague, owner_id, CENTER_A)
    assert exc.value.status_code == 403


# --- Integration Tests: /api/users Endpoints ---

class MockScalarResult:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else ([items] if items else [])

    def scalars(self):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


class FakeUserDB:
    def __init__(self):
        self.users = {}
        self.parent_student_links = set()

    def add_user(self, user):
        self.users[str(user.id)] = user
        self.users[user.email] = user

    async def execute(self, statement):
        query_str = str(statement)
        params = getattr(statement, "_params", {})
        try:
            compiled = statement.compile()
            if compiled.params:
                params.update(compiled.params)
        except Exception:
            pass

        # Extract criteria values
        try:
            for clause in getattr(statement, "_where_criteria", ()):
                right_val = getattr(getattr(clause, "right", None), "value", None)
                if right_val is not None:
                    str_right = str(right_val)
                    if str_right in self.users:
                        return MockScalarResult(self.users[str_right])
                    if isinstance(right_val, str) and right_val in self.users:
                        return MockScalarResult(self.users[right_val])
        except Exception:
            pass

        # Email lookups
        for key, val in params.items():
            if isinstance(val, str) and "@" in val:
                return MockScalarResult(self.users.get(val))

        # UUID lookups
        for key, val in params.items():
            str_val = str(val)
            if str_val in self.users:
                return MockScalarResult(self.users[str_val])

        # String search fallback
        for key, user in self.users.items():
            if key in query_str:
                return MockScalarResult(user)

        if "WHERE" in query_str.upper() or "WHERE" in str(statement).upper():
            return MockScalarResult(None)

        # Listing query: return all users
        results = [u for u in self.users.values() if isinstance(u, User)]
        unique_users = {str(u.id): u for u in results}.values()
        return MockScalarResult(list(unique_users))

    def add(self, obj):
        if isinstance(obj, User):
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()
            self.add_user(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.fixture
def fake_user_db():
    db = FakeUserDB()
    # Seed users
    super_admin = User(
        id=uuid.uuid4(),
        email="super_admin@cams.vn",
        full_name="Super Admin",
        role=Role.SUPER_ADMIN.value,
        center_id=None,
        is_active=True,
        elo_rating=800,
    )
    center_admin_a = User(
        id=uuid.uuid4(),
        email="center_admin_a@cams.vn",
        full_name="Center Admin A",
        role=Role.CENTER_ADMIN.value,
        center_id=CENTER_A,
        is_active=True,
        elo_rating=800,
    )
    teacher_a = User(
        id=uuid.uuid4(),
        email="teacher_a@cams.vn",
        full_name="Teacher A",
        role=Role.TEACHER.value,
        center_id=CENTER_A,
        is_active=True,
        elo_rating=800,
    )
    student_a = User(
        id=uuid.uuid4(),
        email="student_a@cams.vn",
        full_name="Student A",
        role=Role.STUDENT.value,
        center_id=CENTER_A,
        is_active=True,
        elo_rating=800,
    )
    student_b = User(
        id=uuid.uuid4(),
        email="student_b@cams.vn",
        full_name="Student B",
        role=Role.STUDENT.value,
        center_id=CENTER_B,
        is_active=True,
        elo_rating=800,
    )
    db.add_user(super_admin)
    db.add_user(center_admin_a)
    db.add_user(teacher_a)
    db.add_user(student_a)
    db.add_user(student_b)
    return db


@pytest_asyncio.fixture
async def api_client(fake_user_db):
    state = {"current_user": fake_user_db.users["center_admin_a@cams.vn"]}

    async def override_db():
        yield fake_user_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: state["current_user"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.state = state  # Allow switching user in tests
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_center_admin_create_teacher_success(api_client, fake_user_db):
    """center_admin can create a teacher; center_id is forced to caller's center."""
    payload = {
        "email": "new_teacher@cams.vn",
        "password": "Password123!",
        "full_name": "New Teacher",
        "role": "teacher",
        "center_id": str(CENTER_B),  # Attacker attempt to create in Center B
    }
    response = await api_client.post("/api/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_teacher@cams.vn"
    assert data["role"] == "teacher"
    # Forced to CENTER_A, ignoring CENTER_B in payload
    assert data["center_id"] == str(CENTER_A)


@pytest.mark.asyncio
async def test_center_admin_cannot_create_super_admin(api_client):
    """center_admin cannot create super_admin or center_admin."""
    payload = {
        "email": "hacker_admin@cams.vn",
        "password": "Password123!",
        "full_name": "Hacker Admin",
        "role": "super_admin",
    }
    response = await api_client.post("/api/users", json=payload)
    assert response.status_code == 403
    assert "Center admins can only create" in response.json()["detail"]


@pytest.mark.asyncio
async def test_teacher_cannot_create_user(api_client, fake_user_db):
    """Teacher cannot create any user."""
    api_client.state["current_user"] = fake_user_db.users["teacher_a@cams.vn"]
    payload = {
        "email": "new_student@cams.vn",
        "password": "Password123!",
        "full_name": "New Student",
        "role": "student",
    }
    response = await api_client.post("/api/users", json=payload)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_center_user_detail_returns_404(api_client, fake_user_db):
    """Querying user from another center returns 404 Not Found."""
    student_b = fake_user_db.users["student_b@cams.vn"]
    response = await api_client.get(f"/api/users/{student_b.id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_link_parent_student_different_center_rejected(api_client, fake_user_db):
    """Cannot link a parent and student from different centers."""
    parent_a = User(
        id=uuid.uuid4(),
        email="parent_a@cams.vn",
        full_name="Parent A",
        role=Role.PARENT.value,
        center_id=CENTER_A,
        is_active=True,
    )
    fake_user_db.add_user(parent_a)
    student_b = fake_user_db.users["student_b@cams.vn"]

    response = await api_client.post(f"/api/users/{parent_a.id}/students/{student_b.id}")
    # Caller center_admin_a belongs to CENTER_A, student_b belongs to CENTER_B -> 404
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_super_admin_cannot_demote_themselves(api_client, fake_user_db):
    """Super admin cannot change their own role to center_admin or student."""
    super_admin = fake_user_db.users["super_admin@cams.vn"]
    api_client.state["current_user"] = super_admin

    response = await api_client.put(
        f"/api/users/{super_admin.id}",
        json={"role": "center_admin", "full_name": "Demoted Super Admin"}
    )
    assert response.status_code == 400
    assert "Super admin cannot demote their own account" in response.json()["detail"]


@pytest.mark.asyncio
async def test_super_admin_update_profile_and_center_id_none(api_client, fake_user_db):
    """Super admin retains role super_admin and center_id remains None."""
    super_admin = fake_user_db.users["super_admin@cams.vn"]
    api_client.state["current_user"] = super_admin

    response = await api_client.put(
        f"/api/users/{super_admin.id}",
        json={
            "full_name": "Super Admin Updated",
            "phone": "0912345678",
            "role": "super_admin",
            "center_id": str(CENTER_A),
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Super Admin Updated"
    assert data["role"] == "super_admin"
    assert data["center_id"] is None
    assert super_admin.center_id is None


@pytest.mark.asyncio
async def test_update_me_profile_and_password(api_client, fake_user_db):
    """PUT /api/users/me updates profile fields and password."""
    student = fake_user_db.users["student_a@cams.vn"]
    api_client.state["current_user"] = student

    response = await api_client.put(
        "/api/users/me",
        json={
            "full_name": "Student A Updated",
            "phone": "0987654321",
            "bio": "Love chess and solving tactics",
            "password": "NewSecurePassword123!",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Student A Updated"
    assert data["phone"] == "0987654321"
    assert data["bio"] == "Love chess and solving tactics"

    from app.core.security import verify_password
    assert verify_password("NewSecurePassword123!", student.password_hash) is True

