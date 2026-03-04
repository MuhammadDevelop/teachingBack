from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.test import TestSubmission
from app.models.homework import HomeworkSubmission
from app.models.game import GameSubmission
from app.models.exam import ExamSubmission
from app.models.progress import TeacherRating, LessonProgress
from app.schemas.test import TeacherRatingCreate, RatingResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/rating", tags=["rating"])


@router.get("/leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
):
    """Get student leaderboard based on completed lessons + test scores"""
    # Get all students with their scores
    result = await db.execute(
        select(User).where(User.role == "student", User.is_active == True)
    )
    users = result.scalars().all()

    leaderboard = []
    for user in users:
        # Count test scores
        test_result = await db.execute(
            select(func.sum(TestSubmission.score)).where(
                TestSubmission.user_id == user.id,
                TestSubmission.passed == True
            )
        )
        test_score = test_result.scalar() or 0

        # Count completed lessons
        progress_result = await db.execute(
            select(func.count()).where(
                LessonProgress.user_id == user.id,
                LessonProgress.is_completed == True
            )
        )
        completed_lessons = progress_result.scalar() or 0

        # Count exam scores
        exam_result = await db.execute(
            select(func.sum(ExamSubmission.percentage)).where(
                ExamSubmission.user_id == user.id,
                ExamSubmission.passed == True
            )
        )
        exam_score = exam_result.scalar() or 0

        total_score = test_score + (completed_lessons * 5) + exam_score

        if total_score > 0:
            leaderboard.append({
                "user_id": user.id,
                "full_name": user.full_name,
                "total_score": total_score,
                "test_score": test_score,
                "completed_lessons": completed_lessons,
                "exam_score": exam_score,
            })

    leaderboard.sort(key=lambda x: x["total_score"], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    return leaderboard


@router.post("/teacher")
async def rate_teacher(
    data: TeacherRatingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Rate the teacher (1-5)"""
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Baho 1 dan 5 gacha bo'lishi kerak")

    # Check if already rated
    existing = await db.execute(
        select(TeacherRating).where(TeacherRating.user_id == user.id)
    )
    rating = existing.scalar_one_or_none()
    if rating:
        rating.rating = data.rating
    else:
        rating = TeacherRating(user_id=user.id, rating=data.rating)
        db.add(rating)

    await db.commit()
    return {"message": "Baho qo'yildi", "rating": data.rating}


@router.get("/teacher")
async def get_teacher_rating(db: AsyncSession = Depends(get_db)):
    """Get average teacher rating"""
    result = await db.execute(
        select(func.avg(TeacherRating.rating), func.count(TeacherRating.id))
    )
    row = result.one()
    avg_rating = round(float(row[0]), 1) if row[0] else 0
    count = row[1] or 0
    return {"average_rating": avg_rating, "total_ratings": count}
