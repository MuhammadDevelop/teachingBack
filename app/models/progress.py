from datetime import datetime
from sqlalchemy import DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class LessonProgress(Base):
    """Track student progress through each lesson's requirements"""
    __tablename__ = "lesson_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)

    # Video
    video_watched: Mapped[bool] = mapped_column(Boolean, default=False)
    video_watched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Test (must complete within 2h of watching video, 5min test time)
    test_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    test_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Game example (must complete within 3h of watching video)
    game_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    game_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Homework (must submit within 24h of watching video)
    homework_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    homework_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Overall
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="lesson_progress")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="progress")


class TeacherRating(Base):
    """Student rates the teacher"""
    __tablename__ = "teacher_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
