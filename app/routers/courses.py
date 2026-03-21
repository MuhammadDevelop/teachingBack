import re
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, UserCourse
from app.models.course import Module, Course, Lesson
from app.models.progress import LessonProgress
from app.models.exam import Exam
from app.models.payment import Payment
from app.schemas.course import (
    ModuleResponse, ModuleWithCoursesResponse, CourseResponse,
    CourseWithLessonsResponse, LessonDetailResponse,
)
from app.utils.auth import get_current_user, verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/courses", tags=["courses"])


def _normalize_video_url(url):
    """YouTube URL ni embed formatga o'zgartirish"""
    if not url: return url
    url = url.strip()
    match = re.match(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match: return f"https://www.youtube.com/embed/{match.group(1)}"
    match = re.match(r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
    if match: return f"https://www.youtube.com/embed/{match.group(1)}"
    return url


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    if not credentials:
        return None
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("user_id")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()
    except HTTPException:
        return None


@router.get("/modules")
async def get_modules(
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Get all modules with their courses and payment status"""
    result = await db.execute(
        select(Module).where(Module.is_active == True).order_by(Module.order)
    )
    modules = result.scalars().all()

    # Batch load payment statuses
    paid_module_ids = set()
    if user:
        payment_result = await db.execute(
            select(Payment.module_id).where(
                Payment.user_id == user.id,
                Payment.status.in_(["approved", "auto_approved"])
            )
        )
        paid_module_ids = {row[0] for row in payment_result.all()}

    response = []
    for m in modules:
        courses_result = await db.execute(
            select(Course).where(Course.module_id == m.id, Course.is_active == True).order_by(Course.order)
        )
        courses = courses_result.scalars().all()
        response.append({
            "id": m.id, "name": m.name, "slug": m.slug,
            "description": m.description, "price": m.price,
            "order": m.order, "is_active": m.is_active,
            "is_paid": m.id in paid_module_ids,
            "courses": [{
                "id": c.id, "module_id": c.module_id, "name": c.name,
                "slug": c.slug, "description": c.description,
                "thumbnail": c.thumbnail, "order": c.order
            } for c in courses]
        })
    return response


@router.get("/", response_model=list[CourseResponse])
async def get_courses(module_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Course).where(Course.is_active == True)
    if module_id:
        q = q.where(Course.module_id == module_id)
    q = q.order_by(Course.order)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{course_id}", response_model=CourseWithLessonsResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user)
):
    """Get course with lessons and access/progress info"""
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.is_active == True)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    # Check if user has paid for this module
    has_paid = False
    if user:
        # First check UserCourse table
        uc_result = await db.execute(
            select(UserCourse).where(
                UserCourse.user_id == user.id,
                UserCourse.course_id == course.id,
                UserCourse.is_paid == True
            )
        )
        has_paid = uc_result.scalar_one_or_none() is not None

        # Fallback: check Payment table directly
        if not has_paid:
            payment_result = await db.execute(
                select(Payment).where(
                    Payment.user_id == user.id,
                    Payment.module_id == course.module_id,
                    Payment.status.in_(["approved", "auto_approved"])
                )
            )
            if payment_result.scalar_one_or_none():
                # Payment exists but UserCourse missing — auto-create it
                uc = UserCourse(
                    user_id=user.id,
                    course_id=course.id,
                    is_paid=True,
                    purchased_at=datetime.utcnow()
                )
                db.add(uc)
                await db.commit()
                has_paid = True

    # Get lessons
    lessons_result = await db.execute(
        select(Lesson).where(Lesson.course_id == course.id).order_by(Lesson.order)
    )
    lessons = lessons_result.scalars().all()

    # Batch load all progress for this user's lessons
    progress_map = {}
    if user:
        lesson_ids = [l.id for l in lessons]
        if lesson_ids:
            prog_result = await db.execute(
                select(LessonProgress).where(
                    LessonProgress.user_id == user.id,
                    LessonProgress.lesson_id.in_(lesson_ids)
                )
            )
            for prog in prog_result.scalars().all():
                progress_map[prog.lesson_id] = prog

    # Batch load exams for this course
    exam_map = {}
    if user and has_paid:
        exam_result = await db.execute(
            select(Exam).where(Exam.course_id == course.id)
        )
        for exam in exam_result.scalars().all():
            exam_map[exam.after_lesson_order] = exam

    # Batch load exam submissions
    exam_passed_ids = set()
    if user and exam_map:
        from app.models.exam import ExamSubmission
        exam_ids = [e.id for e in exam_map.values()]
        sub_result = await db.execute(
            select(ExamSubmission.exam_id).where(
                ExamSubmission.user_id == user.id,
                ExamSubmission.exam_id.in_(exam_ids),
                ExamSubmission.passed == True
            )
        )
        exam_passed_ids = {row[0] for row in sub_result.all()}

    lessons_with_access = []
    prev_completed = True  # First lesson always accessible

    for lesson in lessons:
        has_access = lesson.is_free or (has_paid and prev_completed)

        # Check progress from batch-loaded map
        progress_data = None
        has_requirements = lesson.test is not None or lesson.homework is not None or lesson.game is not None

        prog = progress_map.get(lesson.id)
        if user:
            if prog:
                progress_data = {
                    "video_watched": prog.video_watched,
                    "video_watched_at": str(prog.video_watched_at) if prog.video_watched_at else None,
                    "test_passed": prog.test_passed,
                    "game_completed": prog.game_completed,
                    "homework_submitted": prog.homework_submitted,
                    "is_completed": prog.is_completed,
                }
                if has_requirements:
                    prev_completed = prog.is_completed
                else:
                    prev_completed = prog.video_watched
            else:
                if lesson.is_free and not has_requirements:
                    prev_completed = True
                elif has_paid and not has_requirements:
                    prev_completed = True
                else:
                    prev_completed = False
        else:
            prev_completed = False

        # Check if exam is needed before this lesson
        if lesson.order > 1 and lesson.order % 12 == 1 and user and has_paid:
            exam = exam_map.get(lesson.order - 1)
            if exam and exam.id not in exam_passed_ids:
                has_access = False

        lessons_with_access.append(LessonDetailResponse(
            id=lesson.id,
            course_id=lesson.course_id,
            title=lesson.title,
            slug=lesson.slug,
            description=lesson.description,
            video_url=_normalize_video_url(lesson.video_url) if has_access else None,
            video_duration=lesson.video_duration,
            order=lesson.order,
            is_free=lesson.is_free,
            has_test=lesson.test is not None,
            has_homework=lesson.homework is not None,
            has_game=lesson.game is not None,
            has_access=has_access,
            progress=progress_data,
        ))

    return CourseWithLessonsResponse(
        id=course.id,
        module_id=course.module_id,
        name=course.name,
        slug=course.slug,
        description=course.description,
        thumbnail=course.thumbnail,
        order=course.order,
        lessons=lessons_with_access,
    )


@router.post("/lessons/{lesson_id}/watch")
async def mark_video_watched(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Mark lesson video as watched - starts time limits for test/game/homework"""
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")

    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()

    if not progress:
        progress = LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            video_watched=True,
            video_watched_at=datetime.utcnow()
        )
        db.add(progress)
    else:
        if not progress.video_watched:
            progress.video_watched = True
            progress.video_watched_at = datetime.utcnow()

    await db.commit()

    # Calculate deadlines
    watch_time = progress.video_watched_at
    return {
        "message": "Video ko'rildi deb belgilandi",
        "video_watched_at": str(watch_time),
        "test_deadline": str(watch_time + timedelta(hours=2)),
        "game_deadline": str(watch_time + timedelta(hours=3)),
        "homework_deadline": str(watch_time + timedelta(hours=24)),
    }


@router.get("/lessons/{lesson_id}/progress")
async def get_lesson_progress(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get progress for a specific lesson, including video_url and description"""
    # Get lesson info
    lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")

    prog_result = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id
        )
    )
    progress = prog_result.scalar_one_or_none()

    base = {
        "title": lesson.title,
        "description": lesson.description,
        "video_url": _normalize_video_url(lesson.video_url),
        "is_free": lesson.is_free,
        "order": lesson.order,
    }

    if not progress:
        return {
            **base,
            "video_watched": False,
            "test_passed": False,
            "game_completed": False,
            "homework_submitted": False,
            "is_completed": False,
        }

    return {
        **base,
        "video_watched": progress.video_watched,
        "video_watched_at": str(progress.video_watched_at) if progress.video_watched_at else None,
        "test_passed": progress.test_passed,
        "game_completed": progress.game_completed,
        "homework_submitted": progress.homework_submitted,
        "is_completed": progress.is_completed,
        "test_deadline": str(progress.video_watched_at + timedelta(hours=2)) if progress.video_watched_at else None,
        "game_deadline": str(progress.video_watched_at + timedelta(hours=3)) if progress.video_watched_at else None,
        "homework_deadline": str(progress.video_watched_at + timedelta(hours=24)) if progress.video_watched_at else None,
    }
