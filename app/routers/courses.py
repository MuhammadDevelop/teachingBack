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
from app.models.homework import Homework, HomeworkSubmission
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
    """YouTube URL ni embed formatga o'zgartirish, boshqa URLlar ham qo'llab-quvvatlanadi"""
    if not url: return url
    url = url.strip()
    # youtu.be short link
    match = re.match(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', url)
    if match: return f"https://www.youtube.com/embed/{match.group(1)}"
    # youtube.com/watch?v=
    match = re.match(r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
    if match: return f"https://www.youtube.com/embed/{match.group(1)}"
    # youtube.com/embed/ — already correct
    if re.match(r'https?://(?:www\.)?youtube\.com/embed/', url):
        return url
    # youtube.com/shorts/
    match = re.match(r'https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)', url)
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
    """Get course with lessons and access/progress info.
    
    LESSON UNLOCK LOGIC:
    - First lesson is always open (if module is paid)
    - Next lesson unlocks ONLY when previous lesson's homework is APPROVED by admin
    - If lesson has no homework, watching the video is enough
    - Tests are for results only, they do NOT unlock anything
    """
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.is_active == True)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    # Check if user has paid for this module
    has_paid = False
    if user:
        uc_result = await db.execute(
            select(UserCourse).where(
                UserCourse.user_id == user.id,
                UserCourse.course_id == course.id,
                UserCourse.is_paid == True
            )
        )
        has_paid = uc_result.scalar_one_or_none() is not None

        if not has_paid:
            payment_result = await db.execute(
                select(Payment).where(
                    Payment.user_id == user.id,
                    Payment.module_id == course.module_id,
                    Payment.status.in_(["approved", "auto_approved"])
                )
            )
            if payment_result.scalar_one_or_none():
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

    # Batch load homework submissions to check approval status
    hw_submission_map = {}
    if user:
        lesson_ids = [l.id for l in lessons]
        if lesson_ids:
            hw_result = await db.execute(
                select(Homework).where(Homework.lesson_id.in_(lesson_ids))
            )
            hw_list = hw_result.scalars().all()
            hw_ids = [h.id for h in hw_list]
            hw_lesson_map = {h.id: h.lesson_id for h in hw_list}
            
            if hw_ids:
                sub_result = await db.execute(
                    select(HomeworkSubmission).where(
                        HomeworkSubmission.user_id == user.id,
                        HomeworkSubmission.homework_id.in_(hw_ids)
                    )
                )
                for sub in sub_result.scalars().all():
                    lesson_id = hw_lesson_map.get(sub.homework_id)
                    if lesson_id:
                        hw_submission_map[lesson_id] = sub

    lessons_with_access = []
    prev_completed = True  # First lesson always accessible

    for lesson in lessons:
        has_access = lesson.is_free or (has_paid and prev_completed)

        # Check progress from batch-loaded map
        progress_data = None
        has_homework = lesson.homework is not None

        prog = progress_map.get(lesson.id)
        hw_sub = hw_submission_map.get(lesson.id)
        
        if user:
            if prog:
                progress_data = {
                    "video_watched": prog.video_watched,
                    "video_watched_at": str(prog.video_watched_at) if prog.video_watched_at else None,
                    "test_passed": prog.test_passed,
                    "homework_submitted": prog.homework_submitted,
                    "homework_graded": hw_sub.is_graded if hw_sub else False,
                    "is_completed": prog.is_completed,
                }
                
                # UNLOCK LOGIC: Next lesson opens only when homework is approved
                if has_homework:
                    # Homework exists: must be submitted AND graded (approved) by admin
                    prev_completed = hw_sub is not None and hw_sub.is_graded
                else:
                    # No homework: watching video is enough
                    prev_completed = prog.video_watched
            else:
                if lesson.is_free and not has_homework:
                    prev_completed = True
                elif has_paid and not has_homework:
                    prev_completed = True
                else:
                    prev_completed = False
        else:
            prev_completed = False

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
            has_homework=has_homework,
            has_game=False,
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
    """Mark lesson video as watched"""
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

    # If lesson has no homework, mark as completed when video is watched
    if lesson.homework is None:
        progress.is_completed = True
        progress.completed_at = datetime.utcnow()

    await db.commit()

    watch_time = progress.video_watched_at
    return {
        "message": "Video ko'rildi deb belgilandi",
        "video_watched_at": str(watch_time),
    }


@router.get("/lessons/{lesson_id}/progress")
async def get_lesson_progress(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get progress for a specific lesson, including video_url and description"""
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
        "has_test": lesson.test is not None,
        "has_homework": lesson.homework is not None,
    }

    if not progress:
        return {
            **base,
            "video_watched": False,
            "test_passed": False,
            "homework_submitted": False,
            "is_completed": False,
        }

    return {
        **base,
        "video_watched": progress.video_watched,
        "video_watched_at": str(progress.video_watched_at) if progress.video_watched_at else None,
        "test_passed": progress.test_passed,
        "homework_submitted": progress.homework_submitted,
        "is_completed": progress.is_completed,
    }
