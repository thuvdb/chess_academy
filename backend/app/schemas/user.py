import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    date_of_birth: date | None = None
    role: str = "student"

class UserCreate(UserBase):
    password: str
    center_id: uuid.UUID | None = None

class UserRead(UserBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    is_active: bool
    elo_rating: int
    avatar_url: str | None = None
    username: str | None = None
    bio: str | None = None
    location: str | None = None
    country: str | None = None
    language: str | None = None
    timezone: str | None = None

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    username: str | None = None
    bio: str | None = None
    location: str | None = None
    country: str | None = None
    language: str | None = None
    timezone: str | None = None
