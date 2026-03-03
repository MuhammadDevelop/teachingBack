from pydantic import BaseModel
from datetime import datetime


class VideoResponse(BaseModel):
    id: int
    title: str
    video_url: str
    duration_seconds: int | None

    class Config:
        from_attributes = True


class LessonResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None
    order: int
    is_free: bool
    duration_minutes: int | None
    videos: list[VideoResponse] = []

    class Config:
        from_attributes = True


class LessonWithAccessResponse(LessonResponse):
    has_access: bool = False


class CourseResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    price: int
    thumbnail: str | None
    lessons: list[LessonResponse] = []

    class Config:
        from_attributes = True


class CourseWithLessonsResponse(CourseResponse):
    lessons: list[LessonWithAccessResponse] = []


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    courses: list[CourseResponse] = []

    class Config:
        from_attributes = True
