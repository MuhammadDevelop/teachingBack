from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserLogin, UserResponse
from app.utils.auth import create_access_token, get_current_user
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

BOT_LINK = "https://t.me/Mdev_02_bot"


def normalize_phone(raw: str) -> str:
    """Normalize phone: remove spaces, +, -, (), and ensure 998 prefix"""
    phone = raw.replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(")", "")
    # Remove leading zeros
    phone = phone.lstrip("0")
    if not phone.startswith("998"):
        phone = "998" + phone
    return phone


@router.post("/register")
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register new user or send code to existing user"""
    settings = get_settings()
    phone = normalize_phone(data.phone)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user:
        return {
            "message": "Telegram botga o'ting va raqamingizni yuboring",
            "bot_link": BOT_LINK,
            "is_new": False,
        }

    role = UserRole.admin.value if phone == settings.admin_phone else UserRole.student.value
    user = User(
        full_name=data.full_name or "Foydalanuvchi",
        phone=phone,
        role=role,
    )
    db.add(user)
    await db.commit()

    return {
        "message": "Ro'yxatdan o'tdingiz! Telegram botga o'ting",
        "bot_link": BOT_LINK,
        "is_new": True,
    }


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with phone + code from bot"""
    phone = normalize_phone(data.phone)
    code = data.code.strip()

    print(f"[LOGIN] phone={phone}, code={code}")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user:
        print(f"[LOGIN] User not found for phone: {phone}")
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi. Avval ro'yxatdan o'ting.")

    print(f"[LOGIN] Found user: id={user.id}, phone={user.phone}, code_in_db={user.verification_code}")

    if not user.verification_code:
        raise HTTPException(status_code=400, detail="Avval Telegram botga raqamingizni yuboring va kodni oling")

    if user.verification_code.strip() != code:
        print(f"[LOGIN] Code mismatch: DB='{user.verification_code}' vs Input='{code}'")
        raise HTTPException(status_code=400, detail=f"Kod noto'g'ri. Tekshiring: {len(code)} ta raqam kiritdingiz")

    if user.code_expires_at and user.code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Kod muddati tugagan. Botdan yangi kod oling.")

    # Success — clear code
    user.is_verified = True
    user.verification_code = None
    user.code_expires_at = None
    await db.commit()

    token = create_access_token({"user_id": user.id, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar": user.avatar,
            "bio": user.bio,
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        avatar=user.avatar,
        bio=user.bio,
        is_active=user.is_active,
        created_at=str(user.created_at),
    )
