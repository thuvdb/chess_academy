from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, 
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserRead
from app.schemas.auth import (
    Token, RefreshRequest, OAuthRequest, 
    AuthConfigResponse, UserPublicRegister
)
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config():
    """Public read-only config indicating allowed auth capabilities."""
    return {
        "allow_public_register": settings.ALLOW_PUBLIC_REGISTER,
        "google_auth_enabled": bool(settings.GOOGLE_CLIENT_ID),
        "facebook_auth_enabled": bool(settings.FACEBOOK_CLIENT_ID),
    }

@router.post("/register", response_model=UserRead)
async def register(user_in: UserPublicRegister, db: AsyncSession = Depends(get_db)):
    if not settings.ALLOW_PUBLIC_REGISTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled. Please contact your center administrator to receive an account.",
        )
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    # Role is strictly forced to 'student', center_id is strictly None for public self-registration.
    user = User(
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name,
        phone=user_in.phone,
        date_of_birth=user_in.date_of_birth,
        role="student",
        center_id=None,
        is_active=True,
        elo_rating=800,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return {
        "access_token": create_access_token({"sub": user_id}),
        "refresh_token": create_refresh_token({"sub": user_id}),
        "token_type": "bearer",
    }

@router.post("/google", response_model=Token)
async def google_auth(req: OAuthRequest, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={req.token}")
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        user_info = resp.json()
        
    email = user_info.get("email")
    google_id = user_info.get("sub")
    avatar_url = user_info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="No email provided by Google")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not found. Please contact your center administrator to create an account before signing in.",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    changed = False
    if not user.google_id:
        user.google_id = google_id
        changed = True
    if not user.avatar_url and avatar_url:
        user.avatar_url = avatar_url
        changed = True
    if changed:
        await db.commit()

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }

@router.post("/facebook", response_model=Token)
async def facebook_auth(req: OAuthRequest, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={req.token}"
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid Facebook token")
        user_info = resp.json()
        
    email = user_info.get("email")
    facebook_id = user_info.get("id")
    picture_data = user_info.get("picture", {}).get("data", {})
    avatar_url = picture_data.get("url")

    if not email:
        raise HTTPException(status_code=400, detail="No email provided by Facebook")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not found. Please contact your center administrator to create an account before signing in.",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    changed = False
    if not user.facebook_id:
        user.facebook_id = facebook_id
        changed = True
    if not user.avatar_url and avatar_url:
        user.avatar_url = avatar_url
        changed = True
    if changed:
        await db.commit()

    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

