from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.chat import ChatMessage
from app.utils.auth import get_current_user, get_current_admin
from app.services.chat_ai import get_gemini_reply
from app.services.telegram_service import send_to_telegram_group

router = APIRouter(prefix="/chat", tags=["chat"])


class MessageSend(BaseModel):
    message: str
    receiver_id: int | None = None  # None = send to admin


@router.post("/send")
async def send_message(
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Student sends message — goes to admin + AI reply + Telegram group"""
    msg = ChatMessage(
        sender_id=user.id,
        receiver_id=data.receiver_id,
        message=data.message,
        is_from_admin=(user.role == "admin"),
    )
    db.add(msg)
    await db.commit()

    # Student xabari — Telegram guruhga yuborish + AI javob
    if user.role != "admin":
        # 1. Telegram guruhga yuborish (admin ko'rishi uchun)
        tg_message = (
            f"💬 <b>Yangi xabar</b>\n\n"
            f"👤 {user.full_name} ({user.phone})\n\n"
            f"📝 {data.message}"
        )
        await send_to_telegram_group(tg_message)

        # 2. AI Auto-reply
        history_result = await db.execute(
            select(ChatMessage).where(
                or_(
                    ChatMessage.sender_id == user.id,
                    ChatMessage.receiver_id == user.id
                )
            ).order_by(ChatMessage.created_at.desc()).limit(10)
        )
        history_msgs = history_result.scalars().all()

        chat_history = []
        for h in reversed(list(history_msgs)):
            role = "user" if h.sender_id == user.id else "model"
            chat_history.append({"role": role, "text": h.message})

        # Gemini AI javob
        reply_text = None
        try:
            reply_text = await get_gemini_reply(data.message, chat_history)
        except Exception as e:
            print(f"⚠️ Gemini xatolik: {e}")

        # Fallback
        if not reply_text:
            reply_text = get_keyword_reply(data.message)

        if reply_text:
            auto_msg = ChatMessage(
                sender_id=0,
                receiver_id=user.id,
                message=reply_text,
                is_from_admin=True,
            )
            db.add(auto_msg)
            await db.commit()

    return {"id": msg.id, "message": "Xabar yuborildi"}


def get_keyword_reply(text: str) -> str:
    """Fallback: keyword-based auto-reply agar Gemini ishlamasa"""
    t = text.lower().strip()

    if any(w in t for w in ["salom", "assalom", "hello", "hi"]):
        return "Assalomu alaykum! 👋 Sizga qanday yordam bera olaman? Admin tez orada javob beradi."

    if any(w in t for w in ["narx", "to'lov", "pul", "qancha", "price", "summa"]):
        return "💰 Kurs narxlari:\n• Kompyuter savodxonligi - 80,000 so'm\n• Dasturlash - 100,000 so'm\n• Montaj - 80,000 so'm\n\nTo'lov uchun 'To'lov' bo'limiga o'ting."

    if any(w in t for w in ["karta", "card", "perevod"]):
        return "💳 To'lov kartasi: 5614 6819 0511 2722\nEga: Orifjonov Muhammaddiyor\nMuddati: 07/30\n\nTo'lovdan so'ng chekni yuklang."

    if any(w in t for w in ["test", "sinov", "savol"]):
        return "📝 Har bir darsda 10 ta test savol bor. Videoni ko'rganingizdan so'ng 2 soat ichida testni yechishingiz kerak."

    if any(w in t for w in ["sertifikat", "certificate"]):
        return "🏆 Kursni muvaffaqiyatli tugatganingizdan so'ng admin sizga sertifikat yuboradi."

    if any(w in t for w in ["yordam", "help", "qanday"]):
        return "🤖 Savolingizga admin tez orada javob beradi.\n• Darslar — Modullar bo'limida\n• To'lov — To'lov bo'limida\n• Test — Dars ko'rilgandan so'ng"

    if any(w in t for w in ["rahmat", "raxmat", "thanks"]):
        return "Arzimaydi! 😊 Yana qanday yordam kerak bo'lsa yozing."

    return "🤖 Xabaringiz qabul qilindi! Admin tez orada javob beradi."


@router.get("/my")
async def get_my_messages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Student gets their chat with admin"""
    result = await db.execute(
        select(ChatMessage).where(
            or_(
                ChatMessage.sender_id == user.id,
                ChatMessage.receiver_id == user.id
            )
        ).order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    # Mark received messages as read
    for m in messages:
        if m.sender_id != user.id and not m.is_read:
            m.is_read = True
    await db.commit()

    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "message": m.message,
        "is_from_admin": m.is_from_admin,
        "is_read": m.is_read,
        "created_at": str(m.created_at),
        "is_mine": m.sender_id == user.id,
    } for m in messages]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(func.count()).where(
            ChatMessage.receiver_id == user.id,
            ChatMessage.is_read == False
        )
    )
    count = result.scalar() or 0
    return {"unread": count}


# ========== ADMIN ENDPOINTS ==========
@router.get("/admin/conversations")
async def get_all_conversations(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin sees all student conversations"""
    result = await db.execute(
        select(ChatMessage.sender_id).where(
            ChatMessage.is_from_admin == False
        ).distinct()
    )
    student_ids = [row[0] for row in result.all()]

    # Batch load all students
    students_result = await db.execute(
        select(User).where(User.id.in_(student_ids))
    )
    students_map = {u.id: u for u in students_result.scalars().all()}

    conversations = []
    for sid in student_ids:
        student = students_map.get(sid)
        if not student:
            continue

        # Last message
        last_msg = await db.execute(
            select(ChatMessage).where(
                or_(ChatMessage.sender_id == sid, ChatMessage.receiver_id == sid)
            ).order_by(ChatMessage.created_at.desc()).limit(1)
        )
        last = last_msg.scalar_one_or_none()

        # Unread count
        unread = await db.execute(
            select(func.count()).where(
                ChatMessage.sender_id == sid,
                ChatMessage.is_from_admin == False,
                ChatMessage.is_read == False
            )
        )

        # Telegram link
        tg_link = None
        if student.telegram_username:
            tg_link = f"https://t.me/{student.telegram_username}"
        elif student.telegram_id:
            tg_link = f"tg://user?id={student.telegram_id}"

        conversations.append({
            "student_id": sid,
            "student_name": student.full_name,
            "student_phone": student.phone,
            "telegram_link": tg_link,
            "last_message": last.message[:50] if last else "",
            "last_time": str(last.created_at) if last else "",
            "unread": unread.scalar() or 0,
        })

    conversations.sort(key=lambda x: x["last_time"], reverse=True)
    return conversations


@router.get("/admin/messages/{student_id}")
async def get_student_messages(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin gets messages with specific student"""
    result = await db.execute(
        select(ChatMessage).where(
            or_(
                ChatMessage.sender_id == student_id,
                ChatMessage.receiver_id == student_id
            )
        ).order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    # Mark student messages as read
    for m in messages:
        if not m.is_from_admin and not m.is_read:
            m.is_read = True
    await db.commit()

    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "message": m.message,
        "is_from_admin": m.is_from_admin,
        "is_read": m.is_read,
        "created_at": str(m.created_at),
    } for m in messages]


@router.post("/admin/reply/{student_id}")
async def admin_reply(
    student_id: int,
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin replies to student"""
    msg = ChatMessage(
        sender_id=admin.id,
        receiver_id=student_id,
        message=data.message,
        is_from_admin=True,
    )
    db.add(msg)
    await db.commit()
    return {"id": msg.id, "message": "Javob yuborildi"}
