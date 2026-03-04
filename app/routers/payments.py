from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import base64

from app.database import get_db
from app.models.user import User, UserCourse
from app.models.course import Module, Course
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentCardInfo
from app.utils.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/card-info", response_model=PaymentCardInfo)
async def get_card_info():
    """Get payment card info to display to student"""
    settings = get_settings()
    return PaymentCardInfo(
        card_number=settings.card_number,
        card_holder=settings.card_holder,
        card_expiry=settings.card_expiry,
    )


@router.post("/submit-check")
async def submit_check(
    module_id: int = Form(...),
    check_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Student uploads payment check/screenshot"""
    # Get module and price
    module_result = await db.execute(select(Module).where(Module.id == module_id))
    module = module_result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Modul topilmadi")

    # Check if already paid
    existing = await db.execute(
        select(Payment).where(
            Payment.user_id == user.id,
            Payment.module_id == module_id,
            Payment.status == "approved"
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu modul uchun to'lov allaqachon qilingan")

    # Check pending payment
    pending = await db.execute(
        select(Payment).where(
            Payment.user_id == user.id,
            Payment.module_id == module_id,
            Payment.status == "pending"
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="To'lov tekshirilmoqda, iltimos kuting")

    # Read and encode the image
    image_data = await check_image.read()
    if len(image_data) > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(status_code=400, detail="Rasm hajmi 10MB dan oshmasligi kerak")

    image_b64 = base64.b64encode(image_data).decode('utf-8')
    content_type = check_image.content_type or "image/jpeg"
    image_url = f"data:{content_type};base64,{image_b64}"

    payment = Payment(
        user_id=user.id,
        module_id=module_id,
        amount=module.price,
        check_image_url=image_url,
        status="pending"
    )
    db.add(payment)
    await db.commit()

    return {
        "message": "To'lov cheki yuborildi, tekshirilmoqda",
        "payment_id": payment.id,
        "status": "pending",
    }


@router.get("/my")
async def get_my_payments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    response = []
    for p in payments:
        module_result = await db.execute(select(Module).where(Module.id == p.module_id))
        module = module_result.scalar_one_or_none()
        response.append({
            "id": p.id,
            "module_id": p.module_id,
            "module_name": module.name if module else "",
            "amount": p.amount,
            "status": p.status,
            "admin_comment": p.admin_comment,
            "created_at": str(p.created_at),
            "reviewed_at": str(p.reviewed_at) if p.reviewed_at else None,
        })
    return response
