from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SendCodeResponse(BaseModel):
    message: str = "Kod Telegram orqali yuborildi"
    phone: str
