from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User, UserCourse
from app.models.course import Category, Course, Lesson, Video
from app.models.payment import Payment
from app.utils.auth import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class CourseCreate(BaseModel):
    category_id: int
    name: str
    slug: str
    description: Optional[str] = None
    price: int
    thumbnail: Optional[str] = None


class LessonCreate(BaseModel):
    course_id: int
    title: str
    slug: str
    description: Optional[str] = None
    order: int = 0
    is_free: bool = False


class VideoCreate(BaseModel):
    lesson_id: int
    title: str
    video_url: str
    duration_seconds: Optional[int] = None


class StudentUpdate(BaseModel):
    is_active: Optional[bool] = None


@router.get("/students")
async def list_students(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(User).where(User.role == "student").order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "phone": u.phone,
            "is_active": u.is_active,
            "created_at": str(u.created_at),
            "courses": len(u.courses) if u.courses else 0
        }
        for u in users
    ]


@router.get("/students/{user_id}")
async def get_student(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(
        select(User).options(selectinload(User.courses).selectinload(UserCourse.course))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    return {
        "id": user.id,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": str(user.created_at),
        "courses": [
            {"course_id": uc.course_id, "course_name": uc.course.name, "is_paid": uc.is_paid}
            for uc in user.courses
        ]
    }


@router.patch("/students/{user_id}")
async def update_student(
    user_id: int,
    data: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    if data.is_active is not None:
        user.is_active = data.is_active
    await db.commit()
    return {"success": True}


@router.post("/categories")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    cat = Category(**data.model_dump())
    db.add(cat)
    await db.commit()
    return {"id": cat.id}


@router.post("/courses")
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    course = Course(**data.model_dump())
    db.add(course)
    await db.commit()
    return {"id": course.id}


@router.post("/lessons")
async def create_lesson(
    data: LessonCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    lesson = Lesson(**data.model_dump())
    db.add(lesson)
    await db.commit()
    return {"id": lesson.id}


@router.post("/videos")
async def create_video(
    data: VideoCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    video = Video(**data.model_dump())
    db.add(video)
    await db.commit()
    return {"id": video.id}


@router.post("/grant-course")
async def grant_course(
    user_id: int,
    course_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    result = await db.execute(select(UserCourse).where(UserCourse.user_id == user_id, UserCourse.course_id == course_id))
    uc = result.scalar_one_or_none()
    if uc:
        uc.is_paid = True
        uc.purchased_at = datetime.utcnow()
    else:
        uc = UserCourse(user_id=user_id, course_id=course_id, is_paid=True, purchased_at=datetime.utcnow())
        db.add(uc)
    await db.commit()
    return {"success": True}
