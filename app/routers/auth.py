from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, SendCodeResponse
from app.utils.auth import create_access_token, get_current_user
from app.services.telegram_service import generate_code
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SendCodeResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register or update user, return telegram bot link"""
    settings = get_settings()
    phone = data.phone.replace("+", "").replace(" ", "").replace("-", "")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if user:
        user.full_name = data.full_name
    else:
        role = "admin" if phone == settings.admin_phone else "student"
        user = User(full_name=data.full_name, phone=phone, role=role)
        db.add(user)
    await db.commit()

    bot_username = ""
    if settings.telegram_bot_token:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe")
                bot_data = resp.json()
                if bot_data.get("ok"):
                    bot_username = bot_data["result"]["username"]
        except Exception:
            pass

    return SendCodeResponse(
        message="Kod olish uchun Telegram botimizga o'ting va telefon raqamingizni yuboring",
        phone=phone,
        bot_link=f"https://t.me/{bot_username}" if bot_username else ""
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Verify code and return JWT token"""
    phone = data.phone.replace("+", "").replace(" ", "").replace("-", "")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if not user.verification_code:
        raise HTTPException(status_code=400, detail="Avval Telegram botdan kod oling")
    if user.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Kod noto'g'ri")
    if user.code_expires_at and user.code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Kod muddati tugagan")

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
            role=user.role,
            avatar=user.avatar,
            bio=user.bio,
            created_at=user.created_at,
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        is_verified=user.is_verified,
        role=user.role,
        avatar=user.avatar,
        bio=user.bio,
        created_at=user.created_at,
    )
