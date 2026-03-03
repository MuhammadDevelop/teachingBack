import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from app.config import get_settings
from app.models.user import User


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


async def send_code_to_user(db: AsyncSession, user: User) -> str:
    code = generate_code()
    user.verification_code = code
    user.code_expires_at = datetime.utcnow() + timedelta(minutes=10)
    await db.commit()
    return code


async def send_telegram_message(chat_id: int, text: str, token: str) -> bool:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        return True
    except Exception:
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Salom! Online Teaching platformasiga xush kelibsiz!</b>\n\n"
        "📱 Ro'yxatdan o'tish uchun telefon raqamingizni yuboring.\n"
        "Keyin sizga login kodi yuboriladi.\n\n"
        "📲 Raqamni quyidagi formatda yuboring:\n"
        "<code>998901234567</code>",
        parse_mode="HTML"
    )


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass  # Handled in bot runner with db access


def create_bot_application():
    settings = get_settings()
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_command))
    return app


async def run_bot_with_db(db_session_factory):
    """Run bot with database session for handling phone/code requests"""
    settings = get_settings()
    if not settings.telegram_bot_token:
        return

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text or ""
        text = text.replace(" ", "").replace("+", "").replace("-", "")
        if text.startswith("998") and len(text) == 12 and text.isdigit():
            async with db_session_factory() as db:
                result = await db.execute(select(User).where(User.phone == text))
                user = result.scalar_one_or_none()
                if user:
                    code = generate_code()
                    user.verification_code = code
                    user.telegram_id = update.effective_user.id
                    user.code_expires_at = datetime.utcnow() + timedelta(minutes=10)
                    await db.commit()
                    await update.message.reply_text(
                        f"✅ Sizning login kodingiz:\n\n<code>{code}</code>\n\n"
                        f"⏱ Kod 10 daqiqa amal qiladi.\n"
                        f"Platformaga kirish uchun ushbu kodni kiriting.",
                        parse_mode="HTML"
                    )
                else:
                    await update.message.reply_text(
                        "❌ Bu raqam ro'yxatdan o'tmagan.\n"
                        "Avval platformada ro'yxatdan o'ting va telefon raqamingizni kiriting."
                    )
        else:
            await update.message.reply_text(
                "📱 Iltimos, to'g'ri formatda raqam yuboring:\n"
                "<code>998901234567</code>",
                parse_mode="HTML"
            )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
