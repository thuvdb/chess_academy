"""
CAMS Admin AI Settings Router — Superadmin dynamic management of LLM providers & configs.
Prefix: /api/admin/ai-settings
Requires: role=super_admin
"""
import logging
import time
import uuid
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.database import get_db
from app.models.ai_settings import AIProvider, AISettings, AISettingsAudit
from app.models.user import User
from app.schemas.ai_settings import (
    AdminAISettingsOverview,
    AIModelsResponse,
    AIProviderCreate,
    AIProviderOut,
    AIProviderTestResponse,
    AIProviderUpdate,
    AISettingsAuditOut,
    AISettingsOut,
    AISettingsUpdate,
)
from app.services.llm.crypto import (
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
    sanitize_sensitive_text,
)
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.manager import (
    invalidate_ai_settings_cache,
    seed_default_ai_settings_if_needed,
)
from app.services.llm.openai_compat_client import OpenAICompatClient

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai-settings",
    tags=["admin-ai-settings"],
    dependencies=[Depends(require_role(["super_admin"]))],
)


def _serialize_provider(provider: AIProvider) -> AIProviderOut:
    """Format AIProvider for public/admin response with masked credentials."""
    raw_key = ""
    has_key = bool(provider.api_key_encrypted)

    if provider.api_key_encrypted:
        try:
            raw_key = decrypt_api_key(provider.api_key_encrypted)
        except Exception:
            raw_key = ""

    masked = mask_api_key(raw_key) if raw_key else ("****" if has_key else "")

    return AIProviderOut(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        models=provider.models or [],
        enabled=provider.enabled,
        reasoning_effort=getattr(provider, "reasoning_effort", None),
        api_key_masked=masked,
        has_key=has_key,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert UUIDs, datetimes, and other non-JSON types to strings."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_make_json_safe(x) for x in obj]
    return obj


async def _record_audit(
    db: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    details: dict,
) -> None:
    """Record an audit trail entry without sensitive API keys."""
    # Ensure details never contain raw or encrypted keys and are strictly JSON-serializable
    sanitized_details = {k: _make_json_safe(v) for k, v in details.items() if "key" not in k.lower()}
    audit_entry = AISettingsAudit(
        user_id=user_id,
        action=action,
        details=sanitized_details,
    )
    db.add(audit_entry)



@router.get("", response_model=AdminAISettingsOverview)
async def get_ai_settings_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Retrieve all configured AI providers and current active settings."""
    settings_record = await db.scalar(select(AISettings).limit(1))
    if not settings_record:
        settings_record, _ = await seed_default_ai_settings_if_needed(db)

    providers_res = await db.execute(select(AIProvider).order_by(AIProvider.created_at.asc()))
    providers = providers_res.scalars().all()

    return AdminAISettingsOverview(
        settings=AISettingsOut.model_validate(settings_record),
        providers=[_serialize_provider(p) for p in providers],
    )


@router.put("", response_model=AISettingsOut)
async def update_ai_settings(
    payload: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Update active AI tutor settings (default/fallback models, temperature, retries)."""
    settings_record = await db.scalar(select(AISettings).limit(1))
    if not settings_record:
        settings_record, _ = await seed_default_ai_settings_if_needed(db)

    # Validate provider references if changed
    if payload.default_provider_id:
        def_prov = await db.get(AIProvider, payload.default_provider_id)
        if not def_prov:
            raise HTTPException(status_code=400, detail="Nhà cung cấp mặc định không tồn tại.")
        if not def_prov.enabled:
            raise HTTPException(status_code=400, detail="Nhà cung cấp mặc định đang bị vô hiệu hóa.")
        settings_record.default_provider_id = payload.default_provider_id

    if payload.fallback_provider_id is not None:
        if payload.fallback_provider_id:
            fb_prov = await db.get(AIProvider, payload.fallback_provider_id)
            if not fb_prov:
                raise HTTPException(status_code=400, detail="Nhà cung cấp dự phòng không tồn tại.")
            settings_record.fallback_provider_id = payload.fallback_provider_id
        else:
            settings_record.fallback_provider_id = None

    if payload.default_model is not None:
        settings_record.default_model = payload.default_model
    if payload.fallback_model is not None:
        settings_record.fallback_model = payload.fallback_model
    if payload.temperature is not None:
        settings_record.temperature = payload.temperature
    if payload.max_output_tokens is not None:
        settings_record.max_output_tokens = payload.max_output_tokens
    if payload.request_timeout_seconds is not None:
        settings_record.request_timeout_seconds = payload.request_timeout_seconds
    if payload.max_retries is not None:
        settings_record.max_retries = payload.max_retries

    settings_record.updated_by = current_user.id
    await _record_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_AI_SETTINGS",
        details=payload.model_dump(mode="json", exclude_unset=True),
    )

    await db.commit()
    await db.refresh(settings_record)
    await invalidate_ai_settings_cache()

    return AISettingsOut.model_validate(settings_record)


@router.post("/providers", response_model=AIProviderOut, status_code=status.HTTP_201_CREATED)
async def create_ai_provider(
    payload: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Create a new LLM provider (Gemini or OpenAI-compatible)."""
    existing = await db.scalar(select(AIProvider).where(AIProvider.name == payload.name))
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Nhà cung cấp với tên '{payload.name}' đã tồn tại.",
        )

    encrypted_key = encrypt_api_key(payload.api_key) if payload.api_key else ""

    new_provider = AIProvider(
        name=payload.name,
        type=payload.type,
        base_url=payload.base_url.rstrip("/") if payload.base_url else None,
        reasoning_effort=payload.reasoning_effort,
        api_key_encrypted=encrypted_key,
        models=payload.models or [],
        enabled=payload.enabled,
    )
    db.add(new_provider)
    await db.flush()

    await _record_audit(
        db=db,
        user_id=current_user.id,
        action="CREATE_AI_PROVIDER",
        details={"provider_id": str(new_provider.id), "name": new_provider.name, "type": new_provider.type},
    )

    await db.commit()
    await db.refresh(new_provider)
    await invalidate_ai_settings_cache()

    return _serialize_provider(new_provider)


@router.put("/providers/{provider_id}", response_model=AIProviderOut)
async def update_ai_provider(
    provider_id: uuid.UUID,
    payload: AIProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Update an existing LLM provider. Preserves existing API key if omitted or empty."""
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp AI.")

    if payload.name and payload.name != provider.name:
        existing = await db.scalar(select(AIProvider).where(AIProvider.name == payload.name))
        if existing:
            raise HTTPException(status_code=400, detail=f"Tên '{payload.name}' đã được sử dụng.")
        provider.name = payload.name

    if payload.type:
        provider.type = payload.type
    if payload.base_url is not None:
        provider.base_url = payload.base_url.rstrip("/") if payload.base_url else None
    if payload.models is not None:
        provider.models = payload.models
    if payload.enabled is not None:
        provider.enabled = payload.enabled
    if "reasoning_effort" in payload.model_fields_set:
        provider.reasoning_effort = payload.reasoning_effort

    # Only update API key if a non-empty string is provided
    if payload.api_key is not None and payload.api_key.strip():
        provider.api_key_encrypted = encrypt_api_key(payload.api_key.strip())

    await _record_audit(
        db=db,
        user_id=current_user.id,
        action="UPDATE_AI_PROVIDER",
        details={"provider_id": str(provider.id), "name": provider.name},
    )

    await db.commit()
    await db.refresh(provider)
    await invalidate_ai_settings_cache()

    return _serialize_provider(provider)


@router.delete("/providers/{provider_id}")
async def delete_ai_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Delete an LLM provider. Prohibits deleting the active default provider."""
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp AI.")

    settings_record = await db.scalar(select(AISettings).limit(1))
    if settings_record and settings_record.default_provider_id == provider_id:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa nhà cung cấp đang được cài làm mặc định. Hãy đổi default provider trước.",
        )

    if settings_record and settings_record.fallback_provider_id == provider_id:
        settings_record.fallback_provider_id = None

    provider_name = provider.name
    await db.delete(provider)

    await _record_audit(
        db=db,
        user_id=current_user.id,
        action="DELETE_AI_PROVIDER",
        details={"provider_id": str(provider_id), "name": provider_name},
    )

    await db.commit()
    await invalidate_ai_settings_cache()

    return {"message": f"Đã xóa nhà cung cấp '{provider_name}' thành công."}


@router.post("/providers/{provider_id}/test", response_model=AIProviderTestResponse)
async def test_ai_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """
    Test connectivity and model generation with a brief test prompt ('Trả lời: OK').
    Measures latency in milliseconds and sanitizes any sensitive credentials in errors.
    """
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp AI.")

    decrypted_key = ""
    if provider.api_key_encrypted:
        try:
            decrypted_key = decrypt_api_key(provider.api_key_encrypted)
        except Exception as e:
            return AIProviderTestResponse(
                success=False,
                latency_ms=0,
                error="Không thể giải mã API key: " + str(e),
            )

    test_model = provider.models[0] if provider.models else (
        "gemini-3.8-flash" if provider.type == "gemini" else "gpt-4o-mini"
    )

    start_time = time.monotonic()
    collected_text = ""

    try:
        if provider.type == "gemini":
            client = GeminiClient(api_key=decrypted_key, default_model=test_model)
            async for chunk in client.stream_chat(
                system_instruction="Chỉ trả lời chính xác: OK",
                messages=[{"role": "user", "content": "Kiểm tra kết nối. Trả lời: OK"}],
                model=test_model,
                temperature=0.1,
                max_output_tokens=200,
            ):
                collected_text += chunk
                if len(collected_text) >= 10:
                    break
        else:
            client = OpenAICompatClient(
                base_url=provider.base_url or "https://api.openai.com/v1",
                api_key=decrypted_key,
                default_model=test_model,
                timeout_seconds=15.0,
                reasoning_effort=getattr(provider, "reasoning_effort", None),
            )
            async for chunk in client.stream_chat(
                system_instruction="Chỉ trả lời chính xác: OK",
                messages=[{"role": "user", "content": "Kiểm tra kết nối. Trả lời: OK"}],
                model=test_model,
                temperature=0.1,
                max_output_tokens=200,
            ):
                collected_text += chunk
                if len(collected_text) >= 10:
                    break

        latency_ms = int((time.monotonic() - start_time) * 1000)
        return AIProviderTestResponse(
            success=True,
            latency_ms=latency_ms,
            response=collected_text.strip() or "OK",
        )

    except Exception as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        safe_err = sanitize_sensitive_text(str(e), known_secrets=[decrypted_key])
        return AIProviderTestResponse(
            success=False,
            latency_ms=latency_ms,
            error=safe_err,
        )


@router.get("/providers/{provider_id}/models", response_model=AIModelsResponse)
async def list_provider_models(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """
    Retrieve model list for a provider.
    For OpenAI-compatible providers, attempts remote discovery via GET {base_url}/models;
    falls back to stored models if unavailable.
    """
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhà cung cấp AI.")

    stored_models = provider.models or []

    if provider.type == "openai_compatible" and provider.base_url:
        decrypted_key = ""
        if provider.api_key_encrypted:
            try:
                decrypted_key = decrypt_api_key(provider.api_key_encrypted)
            except Exception:
                pass

        url = f"{provider.base_url.rstrip('/')}/models"
        headers = {}
        if decrypted_key:
            headers["Authorization"] = f"Bearer {decrypted_key}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    extracted_models = [m.get("id") for m in data if isinstance(m, dict) and "id" in m]
                    if extracted_models:
                        return AIModelsResponse(models=extracted_models, source="remote")
        except Exception as e:
            safe_err = sanitize_sensitive_text(str(e), known_secrets=[decrypted_key])
            return AIModelsResponse(
                models=stored_models,
                source="stored",
                error=f"Không thể kết nối danh sách models từ xa ({safe_err}). Sử dụng danh sách đã lưu.",
            )

    return AIModelsResponse(models=stored_models, source="stored")


@router.get("/audit", response_model=list[AISettingsAuditOut])
async def get_ai_settings_audit_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["super_admin"])),
):
    """Retrieve audit history log for AI settings changes."""
    stmt = (
        select(AISettingsAudit)
        .options(selectinload(AISettingsAudit.user))
        .order_by(AISettingsAudit.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    entries = res.scalars().all()
    out = []
    for e in entries:
        user_name = e.user.full_name if e.user else "Hệ thống"
        out.append(
            AISettingsAuditOut(
                id=e.id,
                user_id=e.user_id,
                user_name=user_name,
                action=e.action,
                details=e.details or {},
                created_at=e.created_at,
            )
        )
    return out

