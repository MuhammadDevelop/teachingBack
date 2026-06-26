"""
Webhook ni qo'lda o'rnatish skripti.
Render ga deploy qilgandan keyin yoki bot ishlamay qolsa ishlatiladi.

Ishlatish: python setup_webhook.py
"""
import sys
import asyncio
import httpx

sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8710392211:AAHwiHmhI4Mb_pl09C0QPJyw3MsaEcxmXSc"
RENDER_URL = "https://teachingback.onrender.com"
WEBHOOK_URL = f"{RENDER_URL}/webhook/telegram"


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Avvalgi webhook ma'lumotlarini ko'rish
        print("[INFO] Webhook holati tekshirilmoqda...")
        resp = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        )
        info = resp.json()
        current_url = info.get('result', {}).get('url', "Yo'q")
        print(f"Hozirgi webhook: {current_url}")
        if info.get('result', {}).get('last_error_message'):
            print(f"[ERROR] Oxirgi xatolik: {info['result']['last_error_message']}")

        # 2. Webhookni o'chirish (tozalash)
        print("\n[INFO] Webhook o'chirilmoqda...")
        resp = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            json={"drop_pending_updates": True}
        )
        print(f"Delete natija: {resp.json()}")

        # 3. Yangi webhook o'rnatish
        print(f"\n[INFO] Yangi webhook o'rnatilmoqda: {WEBHOOK_URL}")
        resp = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            json={
                "url": WEBHOOK_URL,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": True,
            }
        )
        data = resp.json()
        if data.get("ok"):
            print(f"[OK] Webhook muvaffaqiyatli o'rnatildi!")
            print(f"     URL: {WEBHOOK_URL}")
        else:
            print(f"[ERROR] Xatolik: {data}")

        # 4. Tasdiqlash
        print("\n[INFO] Yangi webhook holati:")
        resp = await client.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        )
        result = resp.json()
        print(f"  URL: {result.get('result', {}).get('url', 'Yo`q')}")
        print(f"  Pending updates: {result.get('result', {}).get('pending_update_count', 0)}")
        last_err = result.get('result', {}).get('last_error_message')
        if last_err:
            print(f"  [ERROR] Last error: {last_err}")
        else:
            print("  [OK] Xatolik yo'q")


if __name__ == "__main__":
    asyncio.run(main())
