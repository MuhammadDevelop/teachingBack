"""Quick test: send a message to the Telegram group"""
import asyncio
import httpx

BOT_TOKEN = "8388477765:AAGhtpnHWz5cgLqE359OpMmImichrThMUZY"
CHAT_ID = "5390177377"

async def test():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "chat_id": CHAT_ID,
            "text": "🧪 Test xabar - admin notification ishlayaptimi?",
            "parse_mode": "HTML",
        })
        data = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Response: {data}")

        if not data.get("ok"):
            print(f"\n❌ XATOLIK! chat_id={CHAT_ID} ga yuborib bo'lmadi.")
            print("Guruh chat ID ni olish uchun:")
            print("1. Botni guruhga qo'shing")
            print("2. Guruhda biror xabar yozing")
            print(f"3. https://api.telegram.org/bot{BOT_TOKEN}/getUpdates ni oching")
            print("4. 'chat' > 'id' ni toping (masalan: -1001234567890)")

            # Try getUpdates to find group chat ID
            print("\n🔍 getUpdates dan guruh chat ID ni qidiryapmiz...")
            resp2 = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
            updates = resp2.json()
            print(f"Updates: {updates}")

asyncio.run(test())
