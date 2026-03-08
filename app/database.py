import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Use default if DATABASE_URL is empty in .env
db_url_raw = settings.database_url
if not db_url_raw or db_url_raw.strip() == "":
    db_url_raw = "postgresql+asyncpg://postgres:postgres@localhost:5432/online_teach"

# Create SSL context for Neon/cloud databases
connect_args = {}
if "neon.tech" in db_url_raw or "sslmode=require" in db_url_raw:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args = {"ssl": ssl_ctx}

# Remove sslmode from URL (asyncpg handles ssl via connect_args)
db_url = db_url_raw.split("?")[0] if "sslmode" in db_url_raw else db_url_raw

engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, connect_args=connect_args)
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
