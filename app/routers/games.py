from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.game import GameExample, GameSubmission
from app.models.progress import LessonProgress
from app.schemas.test import GameResponse, GameSubmitRequest, GameSubmissionResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/lesson/{lesson_id}", response_model=GameResponse)
async def get_game_for_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(GameExample).where(GameExample.lesson_id == lesson_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="O'yin misoli topilmadi")
    return game


@router.post("/{game_id}/start")
async def start_game(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Start game example — must be within 3h of watching video"""
    result = await db.execute(select(GameExample).where(GameExample.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="O'yin topilmadi")

    # Check video watched
    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == game.lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()
    if not progress or not progress.video_watched:
        raise HTTPException(status_code=400, detail="Avval videoni ko'ring")

    # Check 3h deadline
    deadline = progress.video_watched_at + timedelta(hours=3)
    if datetime.utcnow() > deadline:
        raise HTTPException(status_code=400, detail="O'yin vaqti tugagan (3 soat ichida ishlash kerak edi)")

    # Check existing
    existing = await db.execute(
        select(GameSubmission).where(
            GameSubmission.user_id == user.id,
            GameSubmission.game_id == game_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="O'yin allaqachon bajarilgan")

    submission = GameSubmission(
        user_id=user.id,
        game_id=game_id,
        started_at=datetime.utcnow()
    )
    db.add(submission)
    await db.commit()

    return {
        "submission_id": submission.id,
        "started_at": str(submission.started_at),
        "game": GameResponse.model_validate(game).model_dump(),
    }


@router.post("/{game_id}/submit")
async def submit_game(
    game_id: int,
    data: GameSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Submit game answer"""
    sub_result = await db.execute(
        select(GameSubmission).where(
            GameSubmission.user_id == user.id,
            GameSubmission.game_id == game_id,
            GameSubmission.is_completed == False
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=400, detail="O'yinni avval boshlang")

    submission.answer_data = data.answer_data
    submission.is_completed = True
    submission.completed_at = datetime.utcnow()
    await db.commit()

    # Update progress
    game_result = await db.execute(select(GameExample).where(GameExample.id == game_id))
    game = game_result.scalar_one_or_none()

    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == game.lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()
    if progress:
        progress.game_completed = True
        progress.game_completed_at = datetime.utcnow()
        if progress.test_passed and progress.game_completed and progress.homework_submitted:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
        await db.commit()

    return {"message": "O'yin misoli muvaffaqiyatli topshirildi", "is_completed": True}
