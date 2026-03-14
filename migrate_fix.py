"""
DB migration script - To'lov va Chat modellaridagi o'zgarishlarni qo'llash.
"""
import asyncio
import ssl
import traceback
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def run_migration():
    db_url = "postgresql+asyncpg://neondb_owner:npg_BGimMTZ1nk6F@ep-blue-sky-aiu68mgk-pooler.c-4.us-east-1.aws.neon.tech/neondb"
    
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    engine = create_async_engine(db_url, connect_args={"ssl": ssl_ctx})
    
    try:
        async with engine.begin() as conn:
            print("Migration boshlandi...")
            
            # 1. check_image_url ni TEXT ga o'zgartirish
            try:
                await conn.execute(text(
                    "ALTER TABLE payments ALTER COLUMN check_image_url TYPE TEXT"
                ))
                print("OK: payments.check_image_url -> TEXT")
            except Exception as e:
                print(f"WARN check_image_url: {e}")
            
            # 2. FK constraint ni topish va olib tashlash
            try:
                result = await conn.execute(text("""
                    SELECT tc.constraint_name 
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = 'chat_messages' 
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND kcu.column_name = 'sender_id'
                """))
                rows = result.fetchall()
                for row in rows:
                    cn = row[0]
                    await conn.execute(text(f'ALTER TABLE chat_messages DROP CONSTRAINT "{cn}"'))
                    print(f"OK: FK constraint '{cn}' olib tashlandi")
                
                if not rows:
                    print("INFO: sender_id FK constraint topilmadi (allaqachon olib tashlangan)")
            except Exception as e:
                print(f"WARN FK: {e}")
            
            print("Migration yakunlandi!")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
