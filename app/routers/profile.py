from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserProfileUpdate
from app.utils.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        is_verified=user.is_verified,
        role=user.role,
        avatar=user.avatar,
        bio=user.bio,
        created_at=user.created_at,
    )


@router.patch("/", response_model=UserResponse)
async def update_profile(
    data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.bio is not None:
        user.bio = data.bio
    if data.avatar is not None:
        user.avatar = data.avatar
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        phone=user.phone,
        is_verified=user.is_verified,
        role=user.role,
        avatar=user.avatar,
        bio=user.bio,
        created_at=user.created_at,
    )


@router.get("/courses")
async def get_my_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get courses enrolled by the current user with progress"""
    from app.models.user import UserCourse
    from app.models.course import Course, Module

    result = await db.execute(
        select(UserCourse).where(UserCourse.user_id == user.id)
    )
    user_courses = result.scalars().all()

    courses_data = []
    for uc in user_courses:
        course_result = await db.execute(
            select(Course).where(Course.id == uc.course_id)
        )
        course = course_result.scalar_one_or_none()
        if course:
            module_result = await db.execute(
                select(Module).where(Module.id == course.module_id)
            )
            module = module_result.scalar_one_or_none()
            courses_data.append({
                "course_id": course.id,
                "course_name": course.name,
                "module_name": module.name if module else "",
                "is_paid": uc.is_paid,
                "progress": uc.progress,
                "purchased_at": str(uc.purchased_at) if uc.purchased_at else None,
            })

    return courses_data
