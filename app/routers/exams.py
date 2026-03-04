import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.exam import Exam, ExamQuestion, ExamSubmission
from app.schemas.test import ExamResponse, ExamQuestionResponse, ExamSubmitRequest, ExamResultResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("/course/{course_id}")
async def get_exams_for_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Exam).where(Exam.course_id == course_id).order_by(Exam.after_lesson_order)
    )
    exams = result.scalars().all()
    response = []
    for exam in exams:
        # Check if user has submitted
        sub_result = await db.execute(
            select(ExamSubmission).where(
                ExamSubmission.user_id == user.id,
                ExamSubmission.exam_id == exam.id
            )
        )
        sub = sub_result.scalar_one_or_none()
        response.append({
            "id": exam.id,
            "title": exam.title,
            "after_lesson_order": exam.after_lesson_order,
            "time_limit": exam.time_limit,
            "passing_score": exam.passing_score,
            "submitted": sub is not None,
            "passed": sub.passed if sub else False,
            "score": sub.percentage if sub else None,
        })
    return response


@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Imtihon topilmadi")

    questions = [
        ExamQuestionResponse(
            id=q.id, question=q.question,
            option_a=q.option_a, option_b=q.option_b,
            option_c=q.option_c, option_d=q.option_d, order=q.order
        )
        for q in sorted(exam.questions, key=lambda x: x.order)
    ]
    return ExamResponse(
        id=exam.id, course_id=exam.course_id, title=exam.title,
        after_lesson_order=exam.after_lesson_order, time_limit=exam.time_limit,
        passing_score=exam.passing_score, questions=questions
    )


@router.post("/{exam_id}/start")
async def start_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Imtihon topilmadi")

    existing = await db.execute(
        select(ExamSubmission).where(
            ExamSubmission.user_id == user.id,
            ExamSubmission.exam_id == exam_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Imtihon allaqachon topshirilgan")

    submission = ExamSubmission(
        user_id=user.id,
        exam_id=exam_id,
        started_at=datetime.utcnow()
    )
    db.add(submission)
    await db.commit()

    return {
        "submission_id": submission.id,
        "time_limit": exam.time_limit,
        "started_at": str(submission.started_at),
        "expires_at": str(submission.started_at + timedelta(seconds=exam.time_limit)),
    }


@router.post("/{exam_id}/submit", response_model=ExamResultResponse)
async def submit_exam(
    exam_id: int,
    data: ExamSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    sub_result = await db.execute(
        select(ExamSubmission).where(
            ExamSubmission.user_id == user.id,
            ExamSubmission.exam_id == exam_id,
            ExamSubmission.completed_at == None
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=400, detail="Imtihonni avval boshlang")

    exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_result.scalar_one_or_none()

    elapsed = (datetime.utcnow() - submission.started_at).total_seconds()
    if elapsed > exam.time_limit + 10:
        raise HTTPException(status_code=400, detail="Imtihon vaqti tugagan")

    score = 0
    total = len(exam.questions)
    for q in exam.questions:
        user_answer = data.answers.get(str(q.id), "").lower()
        if user_answer == q.correct_option.lower():
            score += 1

    percentage = int((score / total) * 100) if total > 0 else 0
    passed = percentage >= exam.passing_score

    submission.answers = json.dumps(data.answers)
    submission.score = score
    submission.total = total
    submission.percentage = percentage
    submission.passed = passed
    submission.completed_at = datetime.utcnow()
    await db.commit()

    return ExamResultResponse(
        id=submission.id,
        exam_id=exam_id,
        score=score,
        total=total,
        percentage=percentage,
        passed=passed,
        started_at=str(submission.started_at),
        completed_at=str(submission.completed_at),
    )
