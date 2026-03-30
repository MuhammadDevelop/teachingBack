"""
Chat AI - Google Gemini REST API bilan ishlaydi
httpx ishlatadi (google-generativeai SDK kerak EMAS)
3 tilda (O'zbek, Rus, Ingliz) gaplasha oladi
"""
import httpx
from app.config import get_settings

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """Sen MDev Online Teaching platformasining professional AI yordamchisisan.
Sening isming MDev AI. Sen do'stona, aqlli va foydali yordamchisan.

🌍 TIL QOIDALARI:
- Foydalanuvchi O'zbekcha yozsa — O'zbekcha javob ber
- Foydalanuvchi Ruscha yozsa — Ruscha javob ber
- Foydalanuvchi Inglizcha yozsa — Inglizcha javob ber
- Aralash yozsa — O'zbekcha javob ber

👋 SALOMLASHISH:
- "salom", "assalomu alaykum" → "Vaalaykum assalom! 👋 Sizga qanday yordam bera olaman?"
- "hello", "hi" → "Hello! 👋 How can I help you today?"
- "привет", "здравствуйте" → "Здравствуйте! 👋 Чем могу помочь?"

📚 PLATFORMADAGI KURSLAR:
1. Kompyuter savodxonligi — Word, Excel, PowerPoint, Canva
2. Dasturlash — HTML, CSS, JavaScript, React, Python, FastAPI
3. Montaj (Video editing) — CapCut, Premiere Pro

👨‍🏫 O'QITUVCHI: Muhammaddiyor Orifjonov (3+ yil IT tajriba)

💳 TO'LOV: 5614 6819 0511 2722 (Orifjonov Muhammaddiyor)
📞 ALOQA: +998889810206

📝 DARS TARTIBI:
1. Modul uchun to'lov → barcha darslar umrbod ochiladi
2. Har bir darsda: Video → Test (10 savol, 7 daq) → Uyga vazifa
3. Vazifani admin tekshiradi (0, 1 yoki 2 baho)
4. Tasdiqlangandan keyin keyingi video ochiladi

QOIDALAR:
- Javoblar QISQA va ANIQ (3-7 jumla)
- Emojilar ishlatishing mumkin 😊
- Bilmasang — "Admin tez orada javob beradi" de
- Parol/shaxsiy ma'lumot berma
- Dasturlash savoli bo'lsa kod misollar bilan javob ber
"""


async def get_gemini_reply(user_message: str, chat_history: list = None) -> str | None:
    """
    Google Gemini REST API bilan javob berish.
    httpx ishlatadi — google-generativeai SDK kerak emas.
    Fallback: gemini-2.0-flash → gemini-1.5-flash
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        print("⚠️ GEMINI_API_KEY topilmadi!")
        return None

    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]

    # Build contents
    contents = []

    # System instruction as first user message
    contents.append({
        "role": "user",
        "parts": [{"text": f"[SYSTEM INSTRUCTION]: {SYSTEM_PROMPT}"}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Tushundim! Men MDev AI yordamchiman. Sizga 3 tilda yordam beraman. 😊"}]
    })

    # Add chat history
    if chat_history:
        for msg in chat_history[-10:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["text"]}]
            })

    # Add current message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    for model_name in models_to_try:
        try:
            url = GEMINI_API_URL.format(model=model_name)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json={"contents": contents},
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    print(f"⚠️ Gemini {model_name} xato: {response.status_code} - {response.text[:200]}")
                    continue

                data = response.json()

                # Extract reply text
                candidates = data.get("candidates", [])
                if not candidates:
                    print(f"⚠️ Gemini {model_name}: candidates bo'sh")
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    continue

                reply = parts[0].get("text", "").strip()

                if not reply:
                    continue

                # Limit length
                if len(reply) > 1000:
                    reply = reply[:997] + "..."

                return reply

        except Exception as e:
            print(f"⚠️ Gemini {model_name} xatolik: {e}")
            continue

    # All models failed
    print("⚠️ Barcha Gemini modellari ishlamadi")
    return None
