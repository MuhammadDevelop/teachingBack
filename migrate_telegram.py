"""
Migration: telegram_username ustunini users jadvaliga qo'shish
Ishlatish: python migrate_telegram.py
"""
import asyncio
from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # telegram_username ustuni qo'shish
        try:
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100)"
            ))
            print("✅ telegram_username ustuni qo'shildi")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️ telegram_username allaqachon mavjud")
            else:
                print(f"❌ Xatolik: {e}")


if __name__ == "__main__":
    asyncio.run(migrate())
