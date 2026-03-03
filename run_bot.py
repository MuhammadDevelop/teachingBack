import asyncio
from app.database import AsyncSessionLocal
from app.services.telegram_service import run_bot_with_db


async def main():
    app = await run_bot_with_db(AsyncSessionLocal)
    if app:
        await app.initialize()
        await app.start()
        print("Bot is running 24/7...")
        await asyncio.Event().wait()
    else:
        print("Set TELEGRAM_BOT_TOKEN in .env to run bot")


if __name__ == "__main__":
    asyncio.run(main())
