from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class GameExample(Base):
    """One game/interactive example per lesson"""
    __tablename__ = "game_examples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: game configuration
    time_limit: Mapped[int] = mapped_column(Integer, default=10800)  # 3 hours in seconds
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="game")


class GameSubmission(Base):
    __tablename__ = "game_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("game_examples.id", ondelete="CASCADE"), nullable=False)
    answer_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: user's answer
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")
    game: Mapped["GameExample"] = relationship("GameExample")
