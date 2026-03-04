import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from telegram import Update
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Salom! MDevning Online Teaching platformasiga xush kelibsiz!</b>\n\n"
        "📱 Login kodi olish uchun telefon raqamingizni yuboring.\n"
        "Avval saytdan ro'yxatdan o'ting, keyin bu yerga raqamingizni yuboring.\n\n"
        "📲 Raqamni quyidagi formatda yuboring:\n"
        "<code>998901234567</code>",
        parse_mode="HTML"
    )


def create_webhook_bot(db_session_factory):
    """Create bot application for webhook mode (Render)"""
    settings = get_settings()
    if not settings.telegram_bot_token:
        return None

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text.replace(" ", "").replace("+", "").replace("-", "")

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
                        "Avval saytda ro'yxatdan o'ting va telefon raqamingizni kiriting."
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


async def run_bot_polling(db_session_factory):
    """Run bot in polling mode (for local development)"""
    app = create_webhook_bot(db_session_factory)
    if not app:
        print("TELEGRAM_BOT_TOKEN not set, bot won't run")
        return

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("🤖 Bot running in polling mode...")
    import asyncio
    await asyncio.Event().wait()


async def setup_webhook(app, webhook_url: str):
    """Set webhook URL for the bot"""
    settings = get_settings()
    if not settings.telegram_bot_token:
        return

    import httpx
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
        resp = await client.post(url, json={"url": webhook_url})
        data = resp.json()
        if data.get("ok"):
            print(f"✅ Webhook set: {webhook_url}")
        else:
            print(f"❌ Webhook error: {data}")
