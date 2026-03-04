import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.test import Test, TestQuestion, TestSubmission
from app.models.progress import LessonProgress
from app.schemas.test import TestResponse, TestQuestionResponse, TestSubmitRequest, TestResultResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("/lesson/{lesson_id}", response_model=TestResponse)
async def get_test_for_lesson(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get test for a lesson (questions without correct answers)"""
    result = await db.execute(
        select(Test).where(Test.lesson_id == lesson_id)
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")

    questions = [
        TestQuestionResponse(
            id=q.id, question=q.question,
            option_a=q.option_a, option_b=q.option_b,
            option_c=q.option_c, option_d=q.option_d,
            order=q.order
        )
        for q in sorted(test.questions, key=lambda x: x.order)
    ]

    return TestResponse(
        id=test.id, lesson_id=test.lesson_id, title=test.title,
        time_limit=test.time_limit, passing_score=test.passing_score,
        questions=questions
    )


@router.post("/{test_id}/start")
async def start_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Start a test — check video watched and 2hr deadline"""
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")

    # Check video watched
    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == test.lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()
    if not progress or not progress.video_watched:
        raise HTTPException(status_code=400, detail="Avval videoni ko'ring")

    # Check 2h deadline
    deadline = progress.video_watched_at + timedelta(hours=2)
    if datetime.utcnow() > deadline:
        raise HTTPException(status_code=400, detail="Test vaqti tugagan (2 soat ichida yechish kerak edi)")

    # Check if already submitted
    existing = await db.execute(
        select(TestSubmission).where(
            TestSubmission.user_id == user.id,
            TestSubmission.test_id == test_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Test allaqachon yechildi")

    # Create submission (started)
    submission = TestSubmission(
        user_id=user.id,
        test_id=test_id,
        started_at=datetime.utcnow()
    )
    db.add(submission)
    await db.commit()

    return {
        "submission_id": submission.id,
        "time_limit": test.time_limit,
        "started_at": str(submission.started_at),
        "expires_at": str(submission.started_at + timedelta(seconds=test.time_limit)),
    }


@router.post("/{test_id}/submit", response_model=TestResultResponse)
async def submit_test(
    test_id: int,
    data: TestSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Submit test answers — auto-grade and update progress"""
    # Find the active submission
    sub_result = await db.execute(
        select(TestSubmission).where(
            TestSubmission.user_id == user.id,
            TestSubmission.test_id == test_id,
            TestSubmission.completed_at == None
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=400, detail="Testni avval boshlang yoki allaqachon topshirilgan")

    # Check time limit
    test_result = await db.execute(select(Test).where(Test.id == test_id))
    test = test_result.scalar_one_or_none()

    elapsed = (datetime.utcnow() - submission.started_at).total_seconds()
    if elapsed > test.time_limit + 10:  # 10 sec grace
        raise HTTPException(status_code=400, detail="Test vaqti tugagan")

    # Grade
    score = 0
    total = len(test.questions)
    for q in test.questions:
        user_answer = data.answers.get(str(q.id), "").lower()
        if user_answer == q.correct_option.lower():
            score += 1

    passed = score >= test.passing_score
    submission.answers = json.dumps(data.answers)
    submission.score = score
    submission.total = total
    submission.passed = passed
    submission.completed_at = datetime.utcnow()
    await db.commit()

    # Update lesson progress if passed
    if passed:
        prog_result = await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user.id,
                LessonProgress.lesson_id == test.lesson_id
            )
        )
        progress = prog_result.scalar_one_or_none()
        if progress:
            progress.test_passed = True
            progress.test_completed_at = datetime.utcnow()
            # Check if all done
            if progress.test_passed and progress.game_completed and progress.homework_submitted:
                progress.is_completed = True
                progress.completed_at = datetime.utcnow()
            await db.commit()

    return TestResultResponse(
        id=submission.id,
        test_id=test_id,
        score=score,
        total=total,
        passed=passed,
        started_at=str(submission.started_at),
        completed_at=str(submission.completed_at),
    )


@router.get("/{test_id}/result", response_model=TestResultResponse)
async def get_test_result(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    sub_result = await db.execute(
        select(TestSubmission).where(
            TestSubmission.user_id == user.id,
            TestSubmission.test_id == test_id
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Test natijasi topilmadi")

    return TestResultResponse(
        id=submission.id,
        test_id=test_id,
        score=submission.score,
        total=submission.total,
        passed=submission.passed,
        started_at=str(submission.started_at) if submission.started_at else None,
        completed_at=str(submission.completed_at) if submission.completed_at else None,
    )
