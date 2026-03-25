from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Test(Base):
    """One test per lesson with multiple questions"""
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    time_limit: Mapped[int] = mapped_column(Integer, default=420)  # seconds (7 min default)
    passing_score: Mapped[int] = mapped_column(Integer, default=7)  # out of 10
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="test")
    questions: Mapped[list["TestQuestion"]] = relationship("TestQuestion", back_populates="test", lazy="selectin", cascade="all, delete-orphan")


class TestQuestion(Base):
    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)  # a, b, c, d
    order: Mapped[int] = mapped_column(Integer, default=0)

    test: Mapped["Test"] = relationship("Test", back_populates="questions")


class TestSubmission(Base):
    __tablename__ = "test_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    answers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string: {"1": "a", "2": "c", ...}
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=10)
    grade: Mapped[int] = mapped_column(Integer, default=0)  # 1, 2, or 3 based on score
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")
    test: Mapped["Test"] = relationship("Test")
