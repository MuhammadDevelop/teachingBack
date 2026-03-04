from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=9, max_length=20)


class UserLogin(BaseModel):
    phone: str = Field(..., min_length=9, max_length=20)
    code: str = Field(..., min_length=4, max_length=10)


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    is_verified: bool
    role: str
    avatar: str | None = None
    bio: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    avatar: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SendCodeResponse(BaseModel):
    message: str = "Kod Telegram orqali yuboriladi"
    phone: str
    bot_link: str = ""
