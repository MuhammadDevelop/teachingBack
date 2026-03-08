from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.certificate import Certificate
from app.utils.auth import get_current_user

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("/my")
async def get_my_certificates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Certificate).where(Certificate.user_id == user.id)
        .order_by(Certificate.created_at.desc())
    )
    certs = result.scalars().all()
    return [{
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "file_url": c.file_url,
        "issued_at": str(c.issued_at),
    } for c in certs]
