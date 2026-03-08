import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update

from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, courses, payments, admin
from app.routers import profile, tests, games, homework, exams, rating, chat, certificates
from app.config import get_settings
from app.services.telegram_service import create_webhook_bot, setup_webhook

settings = get_settings()
bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app
    # Create tables (skip if already exist)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        if "already exists" in str(e):
            print("ℹ️ Jadvallar allaqachon mavjud, o'tkazib yuborildi")
        else:
            raise

    # Setup telegram bot webhook
    bot_app = create_webhook_bot(AsyncSessionLocal)
    if bot_app:
        await bot_app.initialize()
        webhook_base = settings.render_external_url or settings.frontend_url
        if "onrender.com" in webhook_base or settings.render_external_url:
            webhook_url = f"{settings.render_external_url}/webhook/telegram"
            await setup_webhook(bot_app, webhook_url)
            print(f"🤖 Bot webhook mode: {webhook_url}")

    yield

    # Cleanup
    if bot_app:
        await bot_app.shutdown()


app = FastAPI(
    title="MDev Online Teaching Platform",
    version="2.0",
    lifespan=lifespan
)

# CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
if settings.frontend_url:
    allowed_origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(courses.router)
app.include_router(tests.router)
app.include_router(games.router)
app.include_router(homework.router)
app.include_router(exams.router)
app.include_router(payments.router)
app.include_router(rating.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(certificates.router)


@app.get("/")
async def root():
    return {
        "message": "MDev Online Teaching Platform API",
        "version": "2.0",
        "docs": "/docs",
    }


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    global bot_app
    if not bot_app:
        return {"ok": False}

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
