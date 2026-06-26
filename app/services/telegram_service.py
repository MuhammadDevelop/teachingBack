import random
import string
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from app.config import get_settings
from app.models.user import User


def generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Kodni yangilash", callback_data="refresh_code")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "<b>Salom! MDev Online Teaching platformasiga xush kelibsiz!</b>\n\n"
        "Login kodi olish uchun telefon raqamingizni yuboring.\n\n"
        "Raqamni quyidagi formatda yuboring:\n"
        "<code>998901234567</code>\n\n"
        "Oldingi kodingizni yangilash uchun tugmani bosing:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )


def build_bot_app(db_session_factory):
    """Bot Application ni yaratadi (handlers bilan)"""
    settings = get_settings()
    if not settings.telegram_bot_token:
        return None

    async def send_code_to_user(db, user, telegram_id, username=None):
        code = generate_code()
        user.verification_code = code
        user.telegram_id = telegram_id
        if username:
            user.telegram_username = username
        user.code_expires_at = datetime.utcnow() + timedelta(minutes=10)
        await db.commit()
        return code

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        text = update.message.text.replace(" ", "").replace("+", "").replace("-", "")
        telegram_id = update.effective_user.id

        if text.startswith("998") and len(text) == 12 and text.isdigit():
            async with db_session_factory() as db:
                result = await db.execute(select(User).where(User.phone == text))
                user = result.scalar_one_or_none()
                if user:
                    code = await send_code_to_user(db, user, telegram_id, update.effective_user.username)
                    keyboard = [[InlineKeyboardButton("Kodni yangilash", callback_data="refresh_code")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        f"Sizning login kodingiz:\n\n"
                        f"<code>{code}</code>\n\n"
                        f"Kod 10 daqiqa amal qiladi.\n"
                        f"Platformaga kirish uchun ushbu kodni kiriting.\n\n"
                        f"Yangi kod kerak bolsa tugmani bosing:",
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        "Bu raqam royxatdan otmagan.\n"
                        "Avval saytda royxatdan oting va telefon raqamingizni kiriting."
                    )
        else:
            await update.message.reply_text(
                "Iltimos, togri formatda raqam yuboring:\n"
                "<code>998901234567</code>",
                parse_mode="HTML"
            )

    async def handle_refresh_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        telegram_id = update.effective_user.id

        async with db_session_factory() as db:
            result = await db.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user:
                code = generate_code()
                user.verification_code = code
                user.code_expires_at = datetime.utcnow() + timedelta(minutes=10)
                await db.commit()

                keyboard = [[InlineKeyboardButton("Kodni yangilash", callback_data="refresh_code")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"Yangi login kodingiz:\n\n"
                    f"<code>{code}</code>\n\n"
                    f"Kod 10 daqiqa amal qiladi.\n\n"
                    f"Yana yangi kod kerak bolsa tugmani bosing:",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    "Siz hali royxatdan otmagansiz.\n"
                    "Avval telefon raqamingizni yuboring."
                )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_refresh_code, pattern="refresh_code"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


# === WEBHOOK MODE (Render uchun) ===
def create_webhook_bot(db_session_factory):
    """Webhook mode uchun bot (FastAPI bilan birga ishlaydi)"""
    return build_bot_app(db_session_factory)


async def setup_webhook(app, webhook_url: str):
    """Webhook URL ni Telegram ga o'rnatish"""
    settings = get_settings()
    if not settings.telegram_bot_token:
        return

    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Avval eski webhookni o'chirish
        await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/deleteWebhook",
            json={"drop_pending_updates": True}
        )
        # Yangi webhook o'rnatish
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook",
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": True,
            }
        )
        data = resp.json()
        if data.get("ok"):
            print(f"Webhook ornatildi: {webhook_url}")
        else:
            print(f"Webhook xatolik: {data}")


# === POLLING MODE (lokal yoki alohida process) ===
async def run_bot_polling(db_session_factory):
    """Polling mode da botni ishlatish"""
    app = build_bot_app(db_session_factory)
    if not app:
        print("TELEGRAM_BOT_TOKEN yoq, bot ishlamaydi")
        return

    print("Bot polling mode da ishga tushmoqda...")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        print("Bot polling mode da ishlayapti!")
        await asyncio.Event().wait()  # abadiy kutish


# === ADMIN NOTIFICATION ===
async def send_to_telegram_group(message: str):
    """Admin ga Telegram orqali xabar yuborish"""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_group_chat_id:
        print("Telegram bot token yoki chat_id yoq")
        return False

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": settings.telegram_group_chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            resp = await client.post(url, json=payload)
            data = resp.json()
            if data.get("ok"):
                print("Admin ga xabar yuborildi")
                return True
            else:
                print(f"Telegram xatolik: {data.get('description')}")
                return False
    except Exception as e:
        print(f"Telegram yuborishda xatolik: {e}")
        return False


async def send_admin_notification(message: str, db_session_factory=None):
    """Admin ga bildirishnoma yuborish"""
    success = await send_to_telegram_group(message)
    if success:
        return True

    if db_session_factory:
        try:
            settings = get_settings()
            async with db_session_factory() as db:
                result = await db.execute(
                    select(User).where(User.role == "admin", User.telegram_id.isnot(None))
                )
                admin_user = result.scalar_one_or_none()
                if admin_user and admin_user.telegram_id:
                    import httpx
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                            json={
                                "chat_id": admin_user.telegram_id,
                                "text": message,
                                "parse_mode": "HTML",
                            }
                        )
                        data = resp.json()
                        if data.get("ok"):
                            print("Admin ga shaxsiy xabar yuborildi")
                            return True
        except Exception as e:
            print(f"Admin notification xatolik: {e}")

    return False
