import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# 1. URL-ni tozalash va formatlash
db_url = settings.database_url
if db_url and "sslmode=require" in db_url:
    # sslmode=require qismini olib tashlaymiz, chunki asyncpg buni connect_args orqali hal qiladi
    db_url = db_url.split("?")[0]

# 2. Neon.tech uchun maxsus SSL sozlamasi
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# 3. Engine yaratish (Faqat asinxron drayver bilan)
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_ctx}  # SSL-ni shu yerda majburiy ko'rsatamiz
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()