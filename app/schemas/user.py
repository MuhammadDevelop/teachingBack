from pydantic import BaseModel, Field
from datetime import datetime


class UserRegister(BaseModel):
    full_name: str | None = None
    phone: str = Field(..., min_length=9, max_length=20)


class UserLogin(BaseModel):
    phone: str = Field(..., min_length=9, max_length=20)
    code: str = Field(..., min_length=4, max_length=10)


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    role: str
    is_active: bool = True
    avatar: str | None = None
    bio: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    avatar: str | None = None
