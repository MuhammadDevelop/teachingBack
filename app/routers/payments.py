from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserCourse
from app.models.payment import Payment
from app.models.course import Course
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.utils.auth import get_current_user
from app.services.payment_service import create_payme_params, create_click_params
from app.config import get_settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/init", response_model=PaymentResponse)
async def init_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Course).where(Course.id == data.course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    uc_result = await db.execute(
        select(UserCourse).where(UserCourse.user_id == user.id, UserCourse.course_id == course.id)
    )
    uc = uc_result.scalar_one_or_none()
    if uc and uc.is_paid:
        raise HTTPException(status_code=400, detail="Already purchased")

    amount = course.price
    order_id = f"order_{user.id}_{course.id}_{int(datetime.utcnow().timestamp())}"

    payment = Payment(
        user_id=user.id,
        course_id=course.id,
        amount=amount,
        provider=data.provider,
        transaction_id=order_id,
        status="pending"
    )
    db.add(payment)
    await db.commit()

    settings = get_settings()
    if data.provider == "payme":
        params = create_payme_params(amount, order_id, f"{settings.frontend_url}/courses/{course.slug}")
        payment_url = f"https://checkout.paycom.uz/{params}"
    else:
        params = create_click_params(amount, order_id, f"{settings.frontend_url}/courses/{course.slug}")
        payment_url = f"https://my.click.uz/services/pay?params={params}"

    return PaymentResponse(
        id=payment.id,
        amount=amount,
        provider=data.provider,
        status="pending",
        payment_url=payment_url
    )
