from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.homework import Homework, HomeworkSubmission
from app.models.progress import LessonProgress
from app.schemas.test import HomeworkResponse, HomeworkSubmitRequest, HomeworkSubmissionResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/homework", tags=["homework"])


@router.get("/lesson/{lesson_id}", response_model=HomeworkResponse)
async def get_homework_for_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Homework).where(Homework.lesson_id == lesson_id)
    )
    hw = result.scalar_one_or_none()
    if not hw:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi")
    return hw


@router.post("/{hw_id}/submit")
async def submit_homework(
    hw_id: int,
    data: HomeworkSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Submit homework — must be within 24h of watching video"""
    hw_result = await db.execute(select(Homework).where(Homework.id == hw_id))
    hw = hw_result.scalar_one_or_none()
    if not hw:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi")

    # Check video watched
    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == hw.lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()
    if not progress or not progress.video_watched:
        raise HTTPException(status_code=400, detail="Avval videoni ko'ring")

    # Check 24h deadline
    deadline = progress.video_watched_at + timedelta(hours=hw.deadline_hours)
    if datetime.utcnow() > deadline:
        raise HTTPException(status_code=400, detail="Vazifa vaqti tugagan (24 soat ichida topshirish kerak edi)")

    # Check existing
    existing = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.user_id == user.id,
            HomeworkSubmission.homework_id == hw_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Vazifa allaqachon topshirilgan")

    submission = HomeworkSubmission(
        user_id=user.id,
        homework_id=hw_id,
        answer_text=data.answer_text,
        file_url=data.file_url,
        submitted_at=datetime.utcnow()
    )
    db.add(submission)

    # Update progress
    progress.homework_submitted = True
    progress.homework_submitted_at = datetime.utcnow()
    if progress.test_passed and progress.game_completed and progress.homework_submitted:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()

    await db.commit()
    return {"message": "Vazifa muvaffaqiyatli topshirildi", "submission_id": submission.id}


@router.get("/{hw_id}/status")
async def get_homework_status(
    hw_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    sub_result = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.user_id == user.id,
            HomeworkSubmission.homework_id == hw_id
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        return {"submitted": False}

    return {
        "submitted": True,
        "is_graded": submission.is_graded,
        "score": submission.score,
        "admin_comment": submission.admin_comment,
        "submitted_at": str(submission.submitted_at),
        "graded_at": str(submission.graded_at) if submission.graded_at else None,
    }
