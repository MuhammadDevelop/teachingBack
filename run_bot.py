import asyncio
from app.database import AsyncSessionLocal
from app.services.telegram_service import run_bot_polling


async def main():
    """Run bot in polling mode for local development"""
    await run_bot_polling(AsyncSessionLocal)


if __name__ == "__main__":
    asyncio.run(main())
