from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# --- Module ---
class ModuleResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    price: int
    order: int
    is_active: bool = True

    class Config:
        from_attributes = True


class ModuleCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    price: int
    order: int = 0


class ModuleUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    price: int | None = None
    order: int | None = None
    is_active: bool | None = None


# --- Course ---
class CourseResponse(BaseModel):
    id: int
    module_id: int
    name: str
    slug: str
    description: str | None = None
    thumbnail: str | None = None
    order: int

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    module_id: int
    name: str
    slug: str
    description: str | None = None
    thumbnail: str | None = None
    order: int = 0


class CourseUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    order: int | None = None
    is_active: bool | None = None


# --- Lesson ---
class LessonResponse(BaseModel):
    id: int
    course_id: int
    title: str
    slug: str
    description: str | None = None
    video_url: str | None = None
    video_duration: int | None = None
    order: int
    is_free: bool = False
    has_test: bool = False
    has_homework: bool = False
    has_game: bool = False

    class Config:
        from_attributes = True


class LessonDetailResponse(LessonResponse):
    """Lesson with access info and progress"""
    has_access: bool = False
    progress: dict | None = None  # video_watched, test_passed, etc.


class LessonCreate(BaseModel):
    course_id: int
    title: str
    slug: str
    description: str | None = None
    video_url: str | None = None
    video_duration: int | None = None
    order: int = 0
    is_free: bool = False


class LessonUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    description: str | None = None
    video_url: str | None = None
    video_duration: int | None = None
    order: int | None = None
    is_free: bool | None = None


# --- Module with Courses ---
class ModuleWithCoursesResponse(ModuleResponse):
    courses: list[CourseResponse] = []


class CourseWithLessonsResponse(CourseResponse):
    lessons: list[LessonDetailResponse] = []
