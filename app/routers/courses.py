from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.course import Category, Course, Lesson, Video
from app.models.user import UserCourse
from app.schemas.course import CategoryResponse, CourseResponse, LessonResponse, VideoResponse, CourseWithLessonsResponse, LessonWithAccessResponse
from app.utils.auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.auth import verify_token
from fastapi import HTTPException

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/courses", tags=["courses"])


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    if not credentials:
        return None
    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()
    except HTTPException:
        return None


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).order_by(Category.order)
    )
    categories = result.scalars().all()
    return categories


@router.get("/", response_model=list[CourseResponse])
async def get_courses(category_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Course).where(Course.is_active == True)
    if category_id:
        q = q.where(Course.category_id == category_id)
    q = q.order_by(Course.order)
    result = await db.execute(q)
    courses = result.scalars().all()
    return courses


@router.get("/{course_slug}", response_model=CourseWithLessonsResponse)
async def get_course(course_slug: str, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    result = await db.execute(
        select(Course)
        .options(selectinload(Course.lessons).selectinload(Lesson.videos))
        .where(Course.slug == course_slug, Course.is_active == True)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    has_paid = False
    if user:
        uc_result = await db.execute(
            select(UserCourse).where(UserCourse.user_id == user.id, UserCourse.course_id == course.id)
        )
        uc = uc_result.scalar_one_or_none()
        has_paid = uc.is_paid if uc else False

    lessons_with_access = []
    for lesson in sorted(course.lessons, key=lambda x: x.order):
        has_access = lesson.is_free or has_paid
        lessons_with_access.append(LessonWithAccessResponse(
            **{**{k: getattr(lesson, k) for k in ["id", "title", "slug", "description", "order", "is_free", "duration_minutes"]},
             "has_access": has_access,
             "videos": [VideoResponse(id=v.id, title=v.title, video_url=v.video_url, duration_seconds=v.duration_seconds) for v in sorted(lesson.videos, key=lambda x: x.order)]
        }))

    return CourseWithLessonsResponse(
        id=course.id,
        name=course.name,
        slug=course.slug,
        description=course.description,
        price=course.price,
        thumbnail=course.thumbnail,
        lessons=lessons_with_access
    )
