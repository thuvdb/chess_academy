"""
Integration and Unit Tests for Admin AI Settings Endpoints (/api/admin/ai-settings).
Verifies RBAC (403 for non-superadmin), Key Masking, CRUD, Key Preservation, and Test Endpoint.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.deps import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.ai_settings import AIProvider, AISettings, AISettingsAudit
from app.models.user import User
from app.services.llm.crypto import decrypt_api_key, encrypt_api_key


def _make_user(role: str = "super_admin") -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.full_name = f"Mock {role.title()}"
    u.role = role
    u.is_active = True
    u.center_id = uuid.uuid4()
    return u


@pytest.fixture
def test_env():
    super_admin = _make_user("super_admin")
    prov_id = uuid.uuid4()
    raw_key = "sk-Cw4H9988776655443322113GC"
    enc_key = encrypt_api_key(raw_key)

    mock_provider = AIProvider(
        name="Google Gemini",
        type="gemini",
        base_url=None,
        api_key_encrypted=enc_key,
        models=["gemini-3.8-flash"],
        enabled=True,
    )
    mock_provider.id = prov_id
    mock_provider.created_at = datetime.now(timezone.utc)
    mock_provider.updated_at = datetime.now(timezone.utc)

    mock_settings = AISettings(
        id=uuid.uuid4(),
        default_provider_id=prov_id,
        default_model="gemini-3.8-flash",
        fallback_provider_id=None,
        fallback_model=None,
        temperature=0.7,
        max_output_tokens=1500,
        request_timeout_seconds=30,
        max_retries=2,
        updated_at=datetime.now(timezone.utc),
    )

    mock_audit = AISettingsAudit(
        id=uuid.uuid4(),
        user_id=super_admin.id,
        action="UPDATE_AI_SETTINGS",
        details={"temperature": 0.7},
        created_at=datetime.now(timezone.utc),
    )
    mock_audit.user = super_admin

    state = {
        "user": super_admin,
        "providers": {prov_id: mock_provider},
        "settings": mock_settings,
        "audits": [mock_audit],
        "raw_key": raw_key,
    }

    class MockAsyncSession:
        async def scalar(self, stmt):
            stmt_str = str(stmt).lower()
            if "ai_settings" in stmt_str:
                return state["settings"]
            if "ai_providers" in stmt_str and "where" in stmt_str:
                return None
            return None

        async def execute(self, stmt):
            stmt_str = str(stmt).lower()
            mock_res = MagicMock()
            if "ai_settings_audit" in stmt_str:
                mock_res.scalars.return_value.all.return_value = state["audits"]
                return mock_res
            mock_res.scalars.return_value.all.return_value = list(state["providers"].values())
            return mock_res

        async def get(self, model_cls, ident):
            if model_cls == AIProvider:
                return state["providers"].get(ident)
            if model_cls == AISettings:
                return state["settings"]
            return None

        def add(self, obj):
            if isinstance(obj, AIProvider):
                if not getattr(obj, "id", None):
                    obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)
                obj.updated_at = datetime.now(timezone.utc)
                state["providers"][obj.id] = obj
            if isinstance(obj, AISettings):
                state["settings"] = obj
            if isinstance(obj, AISettingsAudit):
                state["audits"].append(obj)

        async def flush(self):
            pass

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

        async def delete(self, obj):
            if isinstance(obj, AIProvider) and obj.id in state["providers"]:
                del state["providers"][obj.id]

    async def _override_db():
        yield MockAsyncSession()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: state["user"]

    yield state

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rbac_non_superadmin_forbidden(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Student role -> 403
        test_env["user"] = _make_user("student")
        resp = await client.get("/api/admin/ai-settings")
        assert resp.status_code == 403

        # Teacher role -> 403
        test_env["user"] = _make_user("teacher")
        resp = await client.get("/api/admin/ai-settings")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_settings_overview_superadmin_masks_key(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_env["user"] = _make_user("super_admin")

        resp = await client.get("/api/admin/ai-settings")
        assert resp.status_code == 200
        data = resp.json()

        assert "settings" in data
        assert "providers" in data
        assert len(data["providers"]) == 1

        prov = data["providers"][0]
        assert prov["name"] == "Google Gemini"
        assert prov["has_key"] is True
        assert prov["api_key_masked"] == "sk-Cw4H...13GC"
        assert test_env["raw_key"] not in str(data)


@pytest.mark.asyncio
async def test_create_and_update_provider_preserves_key_if_empty(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_env["user"] = _make_user("super_admin")

        # 1. Create a new OpenAI-compatible provider
        create_payload = {
            "name": "AgentRouter DeepSeek",
            "type": "openai_compatible",
            "base_url": "https://agentrouter.org/v1",
            "api_key": "sk-agentrouter-secret1234567890",
            "models": ["deepseek-chat", "deepseek-reasoner"],
            "enabled": True,
        }
        create_resp = await client.post("/api/admin/ai-settings/providers", json=create_payload)
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        new_id = created_data["id"]
        assert created_data["name"] == "AgentRouter DeepSeek"
        assert created_data["has_key"] is True
        assert "sk-agen" in created_data["api_key_masked"]

        # Verify encrypted in DB
        created_prov = test_env["providers"][uuid.UUID(new_id)]
        decrypted = decrypt_api_key(created_prov.api_key_encrypted)
        assert decrypted == "sk-agentrouter-secret1234567890"

        # 2. Update provider without sending api_key (or sending empty string)
        update_payload = {
            "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
            "api_key": "",  # Should keep existing key
        }
        update_resp = await client.put(f"/api/admin/ai-settings/providers/{new_id}", json=update_payload)
        assert update_resp.status_code == 200
        updated_data = update_resp.json()
        assert len(updated_data["models"]) == 3
        assert updated_data["has_key"] is True

        # Check key wasn't erased
        assert decrypt_api_key(created_prov.api_key_encrypted) == "sk-agentrouter-secret1234567890"


@pytest.mark.asyncio
async def test_cannot_delete_default_provider(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_env["user"] = _make_user("super_admin")

        default_prov_id = test_env["settings"].default_provider_id
        del_resp = await client.delete(f"/api/admin/ai-settings/providers/{default_prov_id}")
        assert del_resp.status_code == 400
        assert "Không thể xóa nhà cung cấp đang được cài làm mặc định" in del_resp.json()["detail"]


@pytest.mark.asyncio
async def test_test_provider_endpoint(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_env["user"] = _make_user("super_admin")
        prov_id = list(test_env["providers"].keys())[0]

        async def fake_stream(*args, **kwargs):
            yield "OK"

        with patch("app.services.llm.gemini_client.GeminiClient.stream_chat", side_effect=fake_stream):
            test_resp = await client.post(f"/api/admin/ai-settings/providers/{prov_id}/test")
            assert test_resp.status_code == 200
            data = test_resp.json()
            assert data["success"] is True
            assert data["response"] == "OK"
            assert data["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_get_audit_history_superadmin(test_env):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_env["user"] = _make_user("super_admin")
        resp = await client.get("/api/admin/ai-settings/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        entry = data[0]
        assert entry["action"] == "UPDATE_AI_SETTINGS"
        assert "user_name" in entry
        assert entry["user_name"] == "Mock Super_Admin"
        assert "key" not in str(entry["details"]).lower()


@pytest.mark.asyncio
async def test_openai_compat_client_groq_reasoning_and_tokens():
    from app.services.llm.openai_compat_client import OpenAICompatClient

    client = OpenAICompatClient(
        base_url="https://api.groq.com/openai/v1",
        api_key="mock_key",
        default_model="openai/gpt-oss-20b",
    )

    captured_payload = None

    class MockStreamResponse:
        status_code = 200
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"reasoning":"Thinking step"}}]}'
            yield 'data: {"choices":[{"delta":{"content":" Final answer"}}]}'
            yield 'data: [DONE]'

    def mock_stream(method, url, json, headers):
        nonlocal captured_payload
        captured_payload = json
        return MockStreamResponse()

    with patch("httpx.AsyncClient.stream", side_effect=mock_stream):
        tokens = []
        async for chunk in client.stream_chat(
            system_instruction="sys",
            messages=[{"role": "user", "content": "hi"}],
            model="openai/gpt-oss-20b",
            max_output_tokens=1000,
        ):
            tokens.append(chunk)

        assert captured_payload is not None
        assert "max_tokens" in captured_payload
        assert captured_payload["max_tokens"] == 1000
        assert "reasoning_format" not in captured_payload
        # User receives ONLY content, NEVER reasoning
        assert "Thinking step" not in tokens
        assert " Final answer" in tokens


