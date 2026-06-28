"""Webhook endpoint ni to'g'ridan-to'g'ri test qilish"""
import sys
import httpx
import asyncio

sys.stdout.reconfigure(encoding='utf-8')

RENDER_URL = "https://teachingback.onrender.com"

async def main():
    # 1. Server tirikmi?
    print("[1] Server health tekshirilmoqda...")
    try:
        r = httpx.get(f"{RENDER_URL}/health", timeout=30)
        print(f"    Health: {r.text}")
    except Exception as e:
        print(f"    XATO: {e}")
        return

    # 2. Webhook endpointga /start test yuborish
    print("\n[2] /start buyrug'i webhook ga yuborilyapti...")
    payload = {
        "update_id": 999999,
        "message": {
            "message_id": 999,
            "from": {"id": 5390177377, "is_bot": False, "first_name": "TestUser", "username": "MuhammadDevelop"},
            "chat": {"id": 5390177377, "first_name": "TestUser", "type": "private"},
            "date": 1782498850,
            "text": "/start",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}]
        }
    }
    try:
        r = httpx.post(f"{RENDER_URL}/webhook/telegram", json=payload, timeout=30)
        print(f"    Status: {r.status_code}")
        print(f"    Response: {r.text}")
        if r.status_code == 200:
            print("    [OK] Webhook ishlayapti!")
        else:
            print("    [XATO] Webhook ishlamadi!")
    except Exception as e:
        print(f"    XATO: {e}")

asyncio.run(main())
