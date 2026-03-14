from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    student = "student"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.student.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    courses: Mapped[list["UserCourse"]] = relationship("UserCourse", back_populates="user", lazy="selectin")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user", lazy="selectin", foreign_keys="Payment.user_id")
    lesson_progress: Mapped[list["LessonProgress"]] = relationship("LessonProgress", back_populates="user", lazy="selectin")


class UserCourse(Base):
    __tablename__ = "user_courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    last_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="courses")
    course: Mapped["Course"] = relationship("Course", back_populates="users")
