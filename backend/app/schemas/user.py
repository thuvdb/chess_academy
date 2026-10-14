import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, ConfigDict, Field

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    date_of_birth: date | None = None
    role: str = "student"

class UserCreate(UserBase):
    password: str
    center_id: uuid.UUID | None = None

class UserAdminCreate(BaseModel):
    """Schema for user provisioning by super_admin or center_admin."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern="^(super_admin|center_admin|admin|teacher|student|parent)$")
    center_id: uuid.UUID | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    student_ids: list[uuid.UUID] | None = None  # If role is parent, link these students

class UserAdminUpdate(BaseModel):
    """Schema for updating an existing user by super_admin or center_admin."""
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: str | None = Field(default=None, pattern="^(super_admin|center_admin|admin|teacher|student|parent)$")

class UserRead(UserBase):
    id: uuid.UUID
    center_id: uuid.UUID | None = None
    center_name: str | None = None
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

class UserDetailRead(UserRead):
    children: list[UserRead] = []
    parents: list[UserRead] = []

class ParentStudentLinkResponse(BaseModel):
    parent_id: uuid.UUID
    student_id: uuid.UUID
    message: str

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

