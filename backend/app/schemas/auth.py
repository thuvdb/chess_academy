from datetime import date
from pydantic import BaseModel, EmailStr, Field

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class OAuthRequest(BaseModel):
    token: str # ID token for Google, access token for Facebook

class AuthConfigResponse(BaseModel):
    allow_public_register: bool
    google_auth_enabled: bool
    facebook_auth_enabled: bool

class UserPublicRegister(BaseModel):
    """Schema for public self-registration. Strictly disallows role or center_id input."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    date_of_birth: date | None = None
