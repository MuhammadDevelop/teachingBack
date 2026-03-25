from datetime import datetime
from sqlalchemy import DateTime, Integer, ForeignKey, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class WeeklyBonus(Base):
    """Weekly bonus for top-ranked student — allows skipping 1 homework"""
    __tablename__ = "weekly_bonuses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    week_end: Mapped[datetime] = mapped_column(Date, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_for_lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
