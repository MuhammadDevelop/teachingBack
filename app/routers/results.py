"""Student results - test, homework, game natijalari"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.test import Test, TestSubmission
from app.models.homework import Homework, HomeworkSubmission
from app.models.game import GameExample, GameSubmission
from app.models.course import Lesson
from app.utils.auth import get_current_user

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/my")
async def get_my_results(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Student barcha natijalari: testlar, vazifalar, o'yinlar"""
    
    # Test natijalari
    test_results = []
    test_subs = await db.execute(
        select(TestSubmission).where(TestSubmission.user_id == user.id)
        .order_by(TestSubmission.started_at.desc())
    )
    for sub in test_subs.scalars().all():
        test_result = await db.execute(select(Test).where(Test.id == sub.test_id))
        test = test_result.scalar_one_or_none()
        lesson_title = ""
        if test:
            lesson_result = await db.execute(select(Lesson).where(Lesson.id == test.lesson_id))
            lesson = lesson_result.scalar_one_or_none()
            lesson_title = lesson.title if lesson else ""
        
        test_results.append({
            "id": sub.id,
            "test_title": test.title if test else "",
            "lesson_title": lesson_title,
            "score": sub.score,
            "total": sub.total,
            "passed": sub.passed,
            "submitted_at": str(sub.completed_at or sub.started_at),
        })
    
    # Homework natijalari
    hw_results = []
    hw_subs = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.user_id == user.id)
        .order_by(HomeworkSubmission.submitted_at.desc())
    )
    for sub in hw_subs.scalars().all():
        hw_result = await db.execute(select(Homework).where(Homework.id == sub.homework_id))
        hw = hw_result.scalar_one_or_none()
        lesson_title = ""
        if hw:
            lesson_result = await db.execute(select(Lesson).where(Lesson.id == hw.lesson_id))
            lesson = lesson_result.scalar_one_or_none()
            lesson_title = lesson.title if lesson else ""
        
        hw_results.append({
            "id": sub.id,
            "homework_title": hw.title if hw else "",
            "lesson_title": lesson_title,
            "answer_text": sub.answer_text[:100] if sub.answer_text else "",
            "score": sub.score,
            "is_graded": sub.is_graded,
            "admin_comment": sub.admin_comment,
            "submitted_at": str(sub.submitted_at),
        })
    
    # Game natijalari
    game_results = []
    game_subs = await db.execute(
        select(GameSubmission).where(GameSubmission.user_id == user.id)
        .order_by(GameSubmission.started_at.desc())
    )
    for sub in game_subs.scalars().all():
        game_result = await db.execute(select(GameExample).where(GameExample.id == sub.game_id))
        game = game_result.scalar_one_or_none()
        lesson_title = ""
        if game:
            lesson_result = await db.execute(select(Lesson).where(Lesson.id == game.lesson_id))
            lesson = lesson_result.scalar_one_or_none()
            lesson_title = lesson.title if lesson else ""
        
        game_results.append({
            "id": sub.id,
            "game_title": game.title if game else "",
            "lesson_title": lesson_title,
            "score": 0,
            "completed": sub.is_completed,
            "submitted_at": str(sub.completed_at or sub.started_at),
        })
    
    return {
        "tests": test_results,
        "homework": hw_results,
        "games": game_results,
    }
