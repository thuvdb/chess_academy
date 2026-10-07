from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List
import os
import uuid
import shutil
from fastapi import UploadFile, File

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.api.deps import get_current_user
from sqlalchemy.exc import IntegrityError

router = APIRouter()

@router.put("/me", response_model=UserRead)
async def update_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = user_in.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
        
    try:
        await db.commit()
        await db.refresh(current_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Username already taken or invalid data.")
        
    return current_user

@router.get("/members", response_model=List[UserRead])
async def get_members(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ["super_admin", "admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = select(User)
    
    if current_user.role in ["admin", "teacher"]:
        if current_user.center_id:
            query = query.where(or_(User.center_id == current_user.center_id, User.center_id.is_(None)))
        
    if current_user.role == "teacher":
        query = query.where(User.role == "student")
        
    if search:
        query = query.where(or_(
            User.full_name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.username.ilike(f"%{search}%")
        ))
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    ext = file.filename.split(".")[-1]
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    os.makedirs("uploads/avatars", exist_ok=True)
    file_path = os.path.join("uploads/avatars", filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Assuming backend runs on 8000, we'll return an absolute URL.
    # In production, this should use the request base URL.
    from app.core.config import settings
    # Temporary fallback for local dev
    base_url = "http://localhost:8000" 
    avatar_url = f"{base_url}/static/avatars/{filename}"
    return {"avatar_url": avatar_url}
