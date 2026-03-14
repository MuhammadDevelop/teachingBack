from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import base64

from app.database import get_db
from app.models.user import User
from app.models.course import Module
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentCardInfo
from app.utils.auth import get_current_user
from app.config import get_settings
from app.services.payment_ai import verify_payment_check

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
    """Student uploads payment check/screenshot - Admin tekshiradi"""
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
            Payment.status.in_(["approved", "auto_approved"])
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

    # AI bilan chekni tekshirish (faqat admin uchun tavsiya/izoh sifatida)
    ai_comment = ""
    ai_verified = False
    try:
        ai_result = await verify_payment_check(image_url, expected_amount=module.price)
        ai_comment = ai_result.get("ai_comment", "")
        ai_verified = ai_result.get("is_valid", False)
    except Exception as e:
        ai_comment = f"AI tekshirish imkoni bo'lmadi: {str(e)[:100]}"

    # Har doim pending - admin tekshiradi
    payment = Payment(
        user_id=user.id,
        module_id=module_id,
        amount=module.price,
        check_image_url=image_url,
        status="pending",
        ai_verified=ai_verified,
        ai_comment=ai_comment,
    )
    db.add(payment)
    await db.commit()

    return {
        "message": "✅ To'lov cheki yuborildi! Admin tekshirib, tasdiqlagandan so'ng kurslar ochiladi.",
        "payment_id": payment.id,
        "status": "pending",
        "ai_comment": ai_comment,
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
            "ai_comment": p.ai_comment,
            "ai_verified": p.ai_verified,
            "created_at": str(p.created_at),
            "reviewed_at": str(p.reviewed_at) if p.reviewed_at else None,
        })
    return response
