import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from telegram import Update
from sqlalchemy import text, inspect

from app.database import engine, Base, AsyncSessionLocal
from app.routers import auth, courses, payments, admin
from app.routers import profile, tests, games, homework, exams, rating, chat, certificates, results
from app.routers import questions
from app.config import get_settings
from app.services.telegram_service import create_webhook_bot, setup_webhook

settings = get_settings()
bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_app

    # 1. Create tables (skip if already exist)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Jadvallar tayyor")
    except Exception as e:
        print(f"⚠️ create_all: {e}")

    # 2. Auto-migrate: yangi ustunlar qo'shish
    try:
        async with engine.begin() as conn:
            migrations = [
                ("users", "telegram_username", "VARCHAR(100)"),
                ("test_submissions", "grade", "INTEGER DEFAULT 0"),
            ]
            for table_name, col_name, col_type in migrations:
                try:
                    # Ustun mavjudligini tekshirish
                    check_sql = text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name = '{table_name}' AND column_name = '{col_name}'"
                    )
                    result = await conn.execute(check_sql)
                    exists = result.fetchone()
                    if not exists:
                        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ {table_name}.{col_name} qo'shildi")
                    else:
                        print(f"ℹ️ {table_name}.{col_name} allaqachon mavjud")
                except Exception as me:
                    print(f"⚠️ Migration {table_name}.{col_name}: {me}")
    except Exception as e:
        print(f"⚠️ Migration error: {e}")

    # 3. Setup telegram bot webhook
    try:
        bot_app = create_webhook_bot(AsyncSessionLocal)
        if bot_app:
            await bot_app.initialize()
            if settings.render_external_url:
                webhook_url = f"{settings.render_external_url}/webhook/telegram"
                await setup_webhook(bot_app, webhook_url)
                print(f"🤖 Bot webhook: {webhook_url}")
            else:
                print("ℹ️ RENDER_EXTERNAL_URL yo'q")
    except Exception as e:
        print(f"⚠️ Bot setup error: {e}")
        bot_app = None

    yield

    if bot_app:
        try:
            await bot_app.shutdown()
        except:
            pass


app = FastAPI(
    title="MDev Online Teaching Platform",
    version="2.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip siqish — API javoblarni tezlashtirish
app.add_middleware(GZipMiddleware, minimum_size=500)


# Caching middleware — GET so'rovlar uchun qisqa muddatli kesh
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        # Admin endpoint emas bo'lsa, qisqa kesh
        if "/admin/" not in str(request.url.path):
            response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
        else:
            response.headers["Cache-Control"] = "no-cache"
    return response


# Global exception handler — 500 xatoliklarni to'g'ri qaytarish
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ XATOLIK [{request.method} {request.url.path}]: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Serverda xatolik: {str(exc)[:200]}"},
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
app.include_router(results.router)
app.include_router(questions.router)

# Static files — serve uploaded homework files
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


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

    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
    except Exception as e:
        print(f"⚠️ Telegram webhook error: {e}")
    return {"ok": True}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
