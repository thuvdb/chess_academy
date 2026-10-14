"""
Unit & Integration Tests for CAMS-0022 Security Hotfix.
Covers:
  - Auth config endpoint
  - Disallowing public self-registration by default (403)
  - Strict enforcement of role='student' and center_id=None when public registration is enabled
  - Disallowing unauthorized user auto-provisioning via Google and Facebook OAuth (403)
  - Successful OAuth login and linking for pre-existing users
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.user import User


class MockResult:
    def __init__(self, item):
        self._item = item

    def scalars(self):
        return self

    def first(self):
        return self._item

    def all(self):
        return [self._item] if self._item else []


class FakeAsyncSession:
    def __init__(self, existing_users=None):
        self.users = {u.email: u for u in (existing_users or [])}
        self.added = []
        self.committed = False

    async def execute(self, statement):
        try:
            compiled = statement.compile()
            params = compiled.params or {}
            for val in params.values():
                if isinstance(val, str) and val in self.users:
                    return MockResult(self.users[val])
        except Exception:
            pass

        # String fallback search
        query_str = str(statement)
        for email, user in self.users.items():
            if email in query_str:
                return MockResult(user)
        return MockResult(None)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, User):
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()
            self.users[obj.email] = obj

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass

    async def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = uuid.uuid4()


@pytest.fixture
def fake_db():
    return FakeAsyncSession()


@pytest_asyncio.fixture
async def async_client(fake_db):
    async def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()



@pytest.mark.asyncio
async def test_auth_config_endpoint(async_client):
    """Ensure /api/auth/config returns the current security flags."""
    settings.ALLOW_PUBLIC_REGISTER = False
    response = await async_client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert data["allow_public_register"] is False
    assert "google_auth_enabled" in data
    assert "facebook_auth_enabled" in data


@pytest.mark.asyncio
async def test_register_disabled_by_default(async_client):
    """When ALLOW_PUBLIC_REGISTER is False, /register must return 403 Forbidden."""
    settings.ALLOW_PUBLIC_REGISTER = False
    payload = {
        "email": "attacker@cams.vn",
        "password": "Password123!",
        "full_name": "Attacker",
    }
    response = await async_client.post("/api/auth/register", json=payload)
    assert response.status_code == 403
    assert "Public registration is disabled" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_role_and_center_tampering_prevented(async_client, fake_db):
    """When ALLOW_PUBLIC_REGISTER is True, client-injected role or center_id must be ignored and forced to student / None."""
    settings.ALLOW_PUBLIC_REGISTER = True
    fake_center_id = str(uuid.uuid4())
    payload = {
        "email": "student_test@cams.vn",
        "password": "Password123!",
        "full_name": "New Student",
        "role": "super_admin",  # Attacker attempt
        "center_id": fake_center_id,  # Attacker attempt
    }
    response = await async_client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "student_test@cams.vn"
    assert data["role"] == "student"  # Strictly forced to student
    assert data["center_id"] is None  # Strictly forced to None

    # Verify what was saved in the database
    created_user = fake_db.users["student_test@cams.vn"]
    assert created_user.role == "student"
    assert created_user.center_id is None
    settings.ALLOW_PUBLIC_REGISTER = False  # Reset


@pytest.mark.asyncio
async def test_google_auth_rejects_unregistered_email(async_client):
    """Google OAuth must reject unknown emails with 403 instead of auto-creating a student."""
    mock_resp = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "email": "stranger@gmail.com",
            "sub": "google-123456",
            "name": "Stranger Danger",
            "picture": "http://avatar.com/pic.jpg",
        },
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        response = await async_client.post(
            "/api/auth/google",
            json={"token": "mock-google-token"},
        )
        assert response.status_code == 403
        assert "Account not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_facebook_auth_rejects_unregistered_email(async_client):
    """Facebook OAuth must reject unknown emails with 403 instead of auto-creating a student."""
    mock_resp = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "email": "stranger@facebook.com",
            "id": "fb-123456",
            "name": "FB Stranger",
            "picture": {"data": {"url": "http://avatar.com/fb.jpg"}},
        },
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        response = await async_client.post(
            "/api/auth/facebook",
            json={"token": "mock-fb-token"},
        )
        assert response.status_code == 403
        assert "Account not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_google_auth_succeeds_for_existing_user(async_client, fake_db):
    """Google OAuth must issue JWT and link google_id when the user was pre-created by an admin."""
    existing_user = User(
        id=uuid.uuid4(),
        email="existing_student@cams.vn",
        full_name="Valid Student",
        role="student",
        is_active=True,
    )
    fake_db.users[existing_user.email] = existing_user

    mock_resp = SimpleNamespace(
        status_code=200,
        json=lambda: {
            "email": "existing_student@cams.vn",
            "sub": "google-sub-9999",
            "name": "Valid Student",
            "picture": "http://avatar.com/pic.jpg",
        },
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        response = await async_client.post(
            "/api/auth/google",
            json={"token": "mock-valid-google-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert existing_user.google_id == "google-sub-9999"
