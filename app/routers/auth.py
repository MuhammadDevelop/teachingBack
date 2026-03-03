from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, SendCodeResponse
from app.utils.auth import create_access_token, get_current_user
from app.services.telegram_service import send_code_to_user, generate_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SendCodeResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if user:
        user.full_name = data.full_name
        await db.commit()
    else:
        user = User(full_name=data.full_name, phone=data.phone)
        db.add(user)
        await db.commit()
    return SendCodeResponse(
        message="Kod olish uchun Telegram botimizga qo'shiling va telefon raqamingizni yuboring",
        phone=data.phone
    )


@router.post("/send-code", response_model=SendCodeResponse)
async def resend_code(phone: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await send_code_to_user(db, user)
    return SendCodeResponse(phone=phone)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Invalid code")
    if user.code_expires_at and user.code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired")
    user.is_verified = True
    user.verification_code = None
    user.code_expires_at = None
    await db.commit()
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            phone=user.phone,
            is_verified=user.is_verified,
            role=user.role
        )
    )
