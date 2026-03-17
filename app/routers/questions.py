from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.course import Lesson
from app.models.question import LessonQuestion
from app.utils.auth import get_current_user
from app.services.telegram_service import send_to_telegram_group

router = APIRouter(prefix="/questions", tags=["questions"])


class QuestionCreate(BaseModel):
    lesson_id: int
    question_text: str


@router.post("/")
async def submit_question(
    data: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Talaba dars tagida savol yozadi — Telegram guruhga yuboriladi"""
    if not data.question_text.strip():
        raise HTTPException(status_code=400, detail="Savol bo'sh bo'lmasligi kerak")

    # Darsni tekshirish
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == data.lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")

    question = LessonQuestion(
        user_id=user.id,
        lesson_id=data.lesson_id,
        question_text=data.question_text.strip(),
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    # Telegram guruhga yuborish
    tg_message = (
        f"❓ <b>Yangi savol</b>\n\n"
        f"👤 {user.full_name} ({user.phone})\n"
        f"📚 Dars: {lesson.title}\n\n"
        f"💬 {data.question_text.strip()}"
    )
    await send_to_telegram_group(tg_message)

    return {"id": question.id, "message": "Savol yuborildi!"}


@router.get("/{lesson_id}")
async def get_lesson_questions(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Darsning barcha savollari"""
    result = await db.execute(
        select(LessonQuestion)
        .where(LessonQuestion.lesson_id == lesson_id)
        .order_by(LessonQuestion.created_at.desc())
    )
    questions = result.scalars().all()

    response = []
    for q in questions:
        user_result = await db.execute(select(User).where(User.id == q.user_id))
        u = user_result.scalar_one_or_none()
        response.append({
            "id": q.id,
            "user_name": u.full_name if u else "",
            "question_text": q.question_text,
            "created_at": str(q.created_at),
        })
    return response
