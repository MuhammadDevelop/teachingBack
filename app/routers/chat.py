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
from app.services.telegram_service import send_to_telegram_group, send_admin_notification
from app.database import AsyncSessionLocal

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
        # 1. Telegram guruhga/adminga yuborish
        from datetime import datetime as dt
        # Telegram username linkini tayyorlash
        tg_username_line = ""
        if user.telegram_username:
            tg_username_line = f"\n📱 Telegram: @{user.telegram_username} (https://t.me/{user.telegram_username})"
        elif user.telegram_id:
            tg_username_line = f"\n📱 Telegram: <a href='tg://user?id={user.telegram_id}'>Foydalanuvchiga yozish</a>"
        tg_message = (
            f"💬 <b>Yangi xabar</b>\n\n"
            f"👤 {user.full_name} ({user.phone}){tg_username_line}\n"
            f"🕐 {dt.utcnow().strftime('%H:%M %d.%m.%Y')}\n\n"
            f"📝 {data.message}"
        )
        try:
            result = await send_admin_notification(tg_message, db_session_factory=AsyncSessionLocal)
            if not result:
                print(f"⚠️ Admin ga xabar yuborilmadi! Student: {user.full_name}, Xabar: {data.message[:50]}")
        except Exception as e:
            print(f"⚠️ Telegram xabar yuborishda xatolik: {e}")

        # 2. Chat history (EXCLUDING the current message we just saved)
        history_result = await db.execute(
            select(ChatMessage).where(
                or_(
                    ChatMessage.sender_id == user.id,
                    ChatMessage.receiver_id == user.id
                ),
                ChatMessage.id != msg.id  # Exclude current message
            ).order_by(ChatMessage.created_at.desc()).limit(10)
        )
        history_msgs = history_result.scalars().all()

        chat_history = []
        for h in reversed(list(history_msgs)):
            role = "user" if h.sender_id == user.id else "model"
            chat_history.append({"role": role, "text": h.message})

        # 3. Gemini AI javob
        reply_text = None
        try:
            reply_text = await get_gemini_reply(data.message, chat_history)
        except Exception as e:
            print(f"⚠️ Gemini xatolik: {e}")

        # Fallback — keyword reply
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


def detect_lang(text: str) -> str:
    """Detect language: uz, ru, or en"""
    t = text.lower()
    # Russian characters
    if any(c in t for c in "абвгдежзиклмнопрстуфхцчшщъыьэюя"):
        return "ru"
    # English patterns
    en_words = ["hello", "hi", "help", "how", "what", "course", "price", "contact", "thank", "certificate"]
    if any(w in t for w in en_words):
        return "en"
    return "uz"


def get_keyword_reply(text: str) -> str:
    """Robust multilingual keyword-based auto-reply"""
    t = text.lower().strip()
    lang = detect_lang(t)

    # ===== SALOMLASHISH =====
    if any(w in t for w in ["salom", "assalom", "alaykum"]):
        return "Vaalaykum assalom! 👋 Sizga qanday yordam bera olaman?"
    if any(w in t for w in ["hello", "hi ", "hey"]) or t in ["hi", "hey"]:
        return "Hello! 👋 How can I help you?"
    if any(w in t for w in ["привет", "здравст", "салом"]):
        return "Здравствуйте! 👋 Чем могу помочь?"

    # ===== KURS NARXLARI =====
    if any(w in t for w in ["narx", "qancha", "to'lov", "pul", "summa", "baho", "arzon", "qimmat"]):
        return "💰 Kurslarimiz narxlari:\n\n💻 Kompyuter savodxonligi — 100,000 so'm\n⚡ Dasturlash — 130,000 so'm\n🎬 Montaj — 90,000 so'm\n\nTo'lov bir marta — modul umrbod ochiq! 🎉\n💳 Karta: 5614 6819 0511 2722"
    if any(w in t for w in ["price", "cost", "how much", "pay", "cheap", "expensive"]):
        return "💰 Course prices:\n\n💻 Computer Literacy — 100,000 sum\n⚡ Programming — 130,000 sum\n🎬 Video Editing — 90,000 sum\n\nOne-time payment — lifetime access! 🎉\n💳 Card: 5614 6819 0511 2722"
    if any(w in t for w in ["цена", "стоимость", "сколько", "оплат", "дёшево", "дорого"]):
        return "💰 Стоимость курсов:\n\n💻 Компьютерная грамотность — 100 000 сум\n⚡ Программирование — 130 000 сум\n🎬 Монтаж — 90 000 сум\n\nОдноразовый платёж — доступ навсегда! 🎉\n💳 Карта: 5614 6819 0511 2722"

    # ===== KURSLAR =====
    if any(w in t for w in ["kurs", "dars", "modul", "o'rganish", "frontend", "backend", "word", "excel"]):
        return "📚 Bizda quyidagi kurslar mavjud:\n\n💻 Kompyuter savodxonligi — Word, Excel, PowerPoint, Canva\n⚡ Dasturlash — HTML, CSS, JavaScript, React, Python, FastAPI\n🎬 Montaj — CapCut, Premiere Pro\n\nQaysi kurs sizga qiziq? 🤔"
    if any(w in t for w in ["course", "learn", "program", "lesson", "module"]):
        return "📚 We offer:\n\n💻 Computer Literacy — Word, Excel, PowerPoint, Canva\n⚡ Programming — HTML, CSS, JS, React, Python, FastAPI\n🎬 Video Editing — CapCut, Premiere Pro\n\nWhich course interests you? 🤔"
    if any(w in t for w in ["курс", "урок", "обучен", "модул"]):
        return "📚 Наши курсы:\n\n💻 Компьютерная грамотность — Word, Excel, PowerPoint, Canva\n⚡ Программирование — HTML, CSS, JS, React, Python, FastAPI\n🎬 Монтаж — CapCut, Premiere Pro\n\nКакой курс вас интересует? 🤔"

    # ===== DASTURLASH — TEXNIK SAVOLLAR =====
    if any(w in t for w in ["html", "css", "javascript", "js", "react", "python", "fastapi", "code", "kod", "код"]):
        if lang == "en":
            return "💻 Great question about programming!\n\nOur Programming course covers:\n• HTML & CSS — Web page structure and design\n• JavaScript — Interactivity and logic\n• React — Modern frontend framework\n• Python & FastAPI — Backend development\n\nTotal: 130,000 sum. Want to start? 🚀"
        if lang == "ru":
            return "💻 Отличный вопрос о программировании!\n\nНаш курс охватывает:\n• HTML & CSS — Структура и дизайн веб-страниц\n• JavaScript — Интерактивность и логика\n• React — Современный фронтенд фреймворк\n• Python & FastAPI — Бэкенд разработка\n\nВсего: 130 000 сум. Хотите начать? 🚀"
        return "💻 Dasturlash kursi tarkibi:\n\n• HTML & CSS — Web sahifa tuzilishi va dizayni\n• JavaScript — Interaktivlik va logika\n• React — Zamonaviy frontend framework\n• Python & FastAPI — Backend dasturlash\n\nNarxi: 130,000 so'm. Boshlaysizmi? 🚀"

    # ===== RO'YXATDAN O'TISH =====
    if any(w in t for w in ["ro'yxat", "register", "регистрац", "sign up", "akkaunt", "аккаунт"]):
        if lang == "en":
            return "📝 How to register:\n\n1. Enter your phone number\n2. Open our Telegram bot\n3. Get a 6-digit code\n4. Enter the code on the site\n\nIt's free and takes 1 minute! 🎉"
        if lang == "ru":
            return "📝 Как зарегистрироваться:\n\n1. Введите номер телефона\n2. Откройте наш Telegram бот\n3. Получите 6-значный код\n4. Введите код на сайте\n\nБесплатно и займёт 1 минуту! 🎉"
        return "📝 Ro'yxatdan o'tish tartibi:\n\n1. Telefon raqamingizni kiriting\n2. Telegram botimizni oching\n3. 6 raqamli kodni oling\n4. Kodni saytga kiriting\n\nBepul va 1 daqiqa vaqt oladi! 🎉"

    # ===== REYTING =====
    if any(w in t for w in ["reyting", "rating", "рейтинг", "ball", "балл", "score"]):
        if lang == "en":
            return "🏆 Rating system:\n\n• Your scores come from tests and homework\n• All students are ranked on the leaderboard\n• Rating updates weekly\n• Compete with other students! 💪"
        if lang == "ru":
            return "🏆 Система рейтинга:\n\n• Баллы считаются по тестам и заданиям\n• Все студенты в общем рейтинге\n• Обновляется еженедельно\n• Соревнуйтесь с другими! 💪"
        return "🏆 Reyting tizimi:\n\n• Ballaringiz test va vazifalardan hisoblanadi\n• Barcha o'quvchilar umumiy reytingda\n• Har hafta yangilanadi\n• Boshqa o'quvchilar bilan raqobat qiling! 💪"

    # ===== TO'LOV KARTA =====
    if any(w in t for w in ["karta", "card", "perevod", "to'la"]):
        return "💳 To'lov kartasi:\n\n5614 6819 0511 2722\nEga: Orifjonov Muhammaddiyor\nMuddati: 07/30\n\nTo'lovdan so'ng chekni 'To'lov' bo'limida yuklang."

    # ===== ALOQA =====
    if any(w in t for w in ["telefon", "raqam", "aloqa", "bog'lan", "call"]):
        return "📞 Biz bilan bog'lanish:\n\n+998889810206\n\nTelegram yoki telefon orqali murojaat qilishingiz mumkin."
    if any(w in t for w in ["contact", "phone", "reach"]):
        return "📞 Contact us:\n\n+998889810206\n\nYou can reach us via Telegram or phone."
    if any(w in t for w in ["контакт", "телефон", "связ", "номер"]):
        return "📞 Связь с нами:\n\n+998889810206\n\nМожете написать в Telegram или позвонить."

    # ===== TEST =====
    if any(w in t for w in ["test", "sinov", "savol", "imtihon"]):
        return "📝 Har bir darsda 10 ta test savol bor.\n\n• Vaqt: 7 daqiqa\n• Test paytida boshqa sahifaga o'tib bo'lmaydi\n• O'tsa test avtomatik topshiriladi\n• Natija: 0-3 = 1 baho, 4-6 = 2 baho, 7+ = 3 baho"

    # ===== VAZIFA =====
    if any(w in t for w in ["vazifa", "homework", "topshir"]):
        return "📋 Har bir darsda uyga vazifa bor.\n\n• Vazifani topshiring\n• Admin tekshirib baho qo'yadi (0, 1 yoki 2)\n• Tasdiqlangandan keyin keyingi video ochiladi"

    # ===== SERTIFIKAT =====
    if any(w in t for w in ["sertifikat", "certificate", "сертификат"]):
        if lang == "en":
            return "🏆 After successfully completing the course, the admin will send you a certificate."
        if lang == "ru":
            return "🏆 После успешного завершения курса администратор отправит вам сертификат."
        return "🏆 Kursni muvaffaqiyatli tugatganingizdan so'ng admin sizga sertifikat yuboradi."

    # ===== O'QITUVCHI =====
    if any(w in t for w in ["o'qituvchi", "teacher", "ustoz", "преподаватель", "kim"]):
        return "👨‍🏫 O'qituvchi: Muhammaddiyor Orifjonov\n\n• 3+ yil IT sohasida tajriba\n• Full-stack developer\n• Video kontentlar yaratgan"

    # ===== RAHMAT =====
    if any(w in t for w in ["rahmat", "raxmat", "thanks", "thank", "спасибо"]):
        if lang == "en":
            return "You're welcome! 😊 Let me know if you need anything else."
        if lang == "ru":
            return "Пожалуйста! 😊 Обращайтесь, если будут вопросы."
        return "Arzimaydi! 😊 Yana savolingiz bo'lsa yozing."

    # ===== YORDAM =====
    if any(w in t for w in ["yordam", "help", "qanday", "nima", "помощь", "помоги"]):
        if lang == "en":
            return "🤖 I can help you with:\n\n• Course info and prices\n• Payment details\n• Lesson progress\n• Technical questions\n\nJust ask!"
        if lang == "ru":
            return "🤖 Я могу помочь с:\n\n• Информация о курсах\n• Оплата\n• Прогресс уроков\n• Технические вопросы\n\nПросто спрашивайте!"
        return "🤖 Men sizga yordam bera olaman:\n\n• Kurslar haqida\n• To'lov ma'lumotlari\n• Darslar bo'yicha\n• Texnik savollar\n\nBemalol so'rang!"

    # ===== DEFAULT =====
    if lang == "en":
        return "🤖 Thank you for your message! I've noted it.\n\nI can help with:\n• 📚 Courses & prices\n• 💳 Payment info\n• 📝 Test rules\n• 💻 Programming questions\n\nOr contact admin: +998889810206"
    if lang == "ru":
        return "🤖 Спасибо за сообщение!\n\nЯ могу помочь с:\n• 📚 Курсы и цены\n• 💳 Информация об оплате\n• 📝 Правила тестов\n• 💻 Вопросы по программированию\n\nИли свяжитесь с админом: +998889810206"
    return "🤖 Xabaringiz qabul qilindi!\n\nMen sizga yordam bera olaman:\n• 📚 Kurslar va narxlar\n• 💳 To'lov ma'lumotlari\n• 📝 Test qoidalari\n• 💻 Dasturlash savollari\n\nYoki admin bilan bog'laning: +998889810206"


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

    if not student_ids:
        return []

    # Batch load all students
    students_result = await db.execute(
        select(User).where(User.id.in_(student_ids))
    )
    students_map = {u.id: u for u in students_result.scalars().all()}

    # Batch: unread counts per student
    unread_result = await db.execute(
        select(ChatMessage.sender_id, func.count()).where(
            ChatMessage.sender_id.in_(student_ids),
            ChatMessage.is_from_admin == False,
            ChatMessage.is_read == False
        ).group_by(ChatMessage.sender_id)
    )
    unread_map = dict(unread_result.all())

    # Batch: last message per student (using all messages involving each student)
    all_messages = await db.execute(
        select(ChatMessage).where(
            or_(
                ChatMessage.sender_id.in_(student_ids),
                ChatMessage.receiver_id.in_(student_ids)
            )
        ).order_by(ChatMessage.created_at.desc())
    )
    last_msg_map = {}
    for msg in all_messages.scalars().all():
        sid = msg.sender_id if msg.sender_id in students_map else msg.receiver_id
        if sid not in last_msg_map:
            last_msg_map[sid] = msg

    conversations = []
    for sid in student_ids:
        student = students_map.get(sid)
        if not student:
            continue

        last = last_msg_map.get(sid)

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
            "unread": unread_map.get(sid, 0),
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
