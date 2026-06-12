import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.course import Lesson
from app.models.homework import Homework, HomeworkSubmission
from app.models.progress import LessonProgress
from app.schemas.test import HomeworkResponse
from app.utils.auth import get_current_user
from app.services.cloudinary_service import upload_to_cloudinary

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
        # Auto-create homework for this lesson
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            raise HTTPException(status_code=404, detail="Dars topilmadi")
        hw = Homework(
            lesson_id=lesson_id,
            title=f"{lesson.title} - Uyga vazifa",
            description="Dars bo'yicha uyga vazifangizni bajaring va topshiring.",
            deadline_hours=24
        )
        db.add(hw)
        await db.commit()
        await db.refresh(hw)
    return hw


@router.post("/{hw_id}/upload")
async def upload_homework_file(
    hw_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Upload a homework file to Cloudinary — returns the file URL"""
    hw_result = await db.execute(select(Homework).where(Homework.id == hw_id))
    hw = hw_result.scalar_one_or_none()
    if not hw:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi")

    # Check file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fayl hajmi 10MB dan oshmasin")

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    unique_name = f"{user.id}_{hw_id}_{uuid.uuid4().hex[:8]}"
    if ext:
        unique_name = f"{unique_name}.{ext}"

    # Upload to Cloudinary
    try:
        result = await upload_to_cloudinary(contents, unique_name)
        file_url = result["url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fayl yuklashda xatolik: {str(e)}")

    return {"file_url": file_url, "filename": file.filename}


@router.post("/{hw_id}/submit")
async def submit_homework(
    hw_id: int,
    answer_text: str = Form(None),
    file_url: str = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Submit homework — supports text, file URL, or file upload to Cloudinary.
    If already submitted, update the existing submission.
    Status becomes 'pending' (not graded) until admin approves.
    """
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

    # Handle file upload to Cloudinary
    uploaded_file_url = file_url
    if file and file.filename:
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Fayl hajmi 10MB dan oshmasin")

        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
        unique_name = f"{user.id}_{hw_id}_{uuid.uuid4().hex[:8]}"
        if ext:
            unique_name = f"{unique_name}.{ext}"

        try:
            result = await upload_to_cloudinary(contents, unique_name)
            uploaded_file_url = result["url"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fayl yuklashda xatolik: {str(e)}")

    if not answer_text and not uploaded_file_url:
        raise HTTPException(status_code=400, detail="Javob matni yoki fayl yuklang")

    # Check existing submission — allow resubmission (unlimited)
    existing_result = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.user_id == user.id,
            HomeworkSubmission.homework_id == hw_id
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        # Update existing submission — reset grading
        existing.answer_text = answer_text
        existing.file_url = uploaded_file_url
        existing.is_graded = False
        existing.score = None
        existing.admin_comment = None
        existing.graded_at = None
        existing.submitted_at = datetime.utcnow()
        submission = existing
    else:
        # New submission
        submission = HomeworkSubmission(
            user_id=user.id,
            homework_id=hw_id,
            answer_text=answer_text,
            file_url=uploaded_file_url,
            submitted_at=datetime.utcnow()
        )
        db.add(submission)

    # Mark homework submitted (pending admin review)
    progress.homework_submitted = True
    progress.homework_submitted_at = datetime.utcnow()
    # Reset completion — admin needs to re-approve after resubmission
    progress.is_completed = False
    progress.completed_at = None

    await db.commit()
    await db.refresh(submission)
    return {
        "message": "Vazifa muvaffaqiyatli topshirildi! Admin tekshirishini kuting.",
        "submission_id": submission.id,
        "status": "pending"
    }


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
        "answer_text": submission.answer_text,
        "file_url": submission.file_url,
    }
