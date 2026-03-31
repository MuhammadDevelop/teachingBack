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

TIL QOIDALARI:
- Foydalanuvchi O'zbekcha yozsa — O'zbekcha javob ber
- Foydalanuvchi Ruscha yozsa — Ruscha javob ber
- Foydalanuvchi Inglizcha yozsa — Inglizcha javob ber

SALOMLASHISH:
- "salom", "assalomu alaykum" → "Vaalaykum assalom! Sizga qanday yordam bera olaman?"
- "hello", "hi" → "Hello! How can I help you today?"
- "привет" → "Здравствуйте! Чем могу помочь?"

PLATFORMADAGI KURSLAR:
1. Kompyuter savodxonligi — Word, Excel, PowerPoint, Canva
2. Dasturlash — HTML, CSS, JavaScript, React, Python, FastAPI
3. Montaj — CapCut, Premiere Pro

O'QITUVCHI: Muhammaddiyor Orifjonov (3+ yil IT tajriba)
TO'LOV KARTA: 5614 6819 0511 2722 (Orifjonov Muhammaddiyor)
ALOQA: +998889810206

DARS TARTIBI: Modul uchun to'lov → Video → Test (10 savol, 7 daq) → Uyga vazifa → Keyingi dars

QOIDALAR:
- Javoblar QISQA va ANIQ bo'lsin (3-5 jumla)
- Emojilar ishlat
- Bilmasang "Bu haqida admin batafsil javob beradi" de
- Parol/shaxsiy ma'lumot berma
- Dasturlash savoli bo'lsa kod misol ber
"""


async def get_gemini_reply(user_message: str, chat_history: list = None) -> str | None:
    """
    Google Gemini REST API bilan javob berish.
    httpx ishlatadi — google-generativeai SDK kerak emas.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        print("⚠️ GEMINI_API_KEY topilmadi!")
        return None

    # Build contents with proper role alternation
    contents = []

    # Add chat history with role deduplication
    if chat_history:
        last_role = None
        for msg in chat_history[-8:]:
            role = "user" if msg.get("role") == "user" else "model"
            # Gemini requires alternating roles - merge consecutive same-role messages
            if role == last_role and contents:
                contents[-1]["parts"][0]["text"] += "\n" + msg["text"]
            else:
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["text"]}]
                })
                last_role = role

    # Add current message
    # If last message was also "user", merge it
    if contents and contents[-1]["role"] == "user":
        contents[-1]["parts"][0]["text"] += "\n" + user_message
    else:
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })

    # Ensure contents starts with "user" role (Gemini requirement)
    if contents and contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "salom"}]})

    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]

    for model_name in models_to_try:
        try:
            url = GEMINI_API_URL.format(model=model_name)

            request_body = {
                "contents": contents,
                "systemInstruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "generationConfig": {
                    "maxOutputTokens": 300,
                    "temperature": 0.7,
                }
            }

            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.post(
                    url,
                    params={"key": settings.gemini_api_key},
                    json=request_body,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    error_text = response.text[:300] if response.text else "No response"
                    print(f"⚠️ Gemini {model_name} HTTP {response.status_code}: {error_text}")
                    continue

                data = response.json()

                # Extract reply
                candidates = data.get("candidates", [])
                if not candidates:
                    print(f"⚠️ Gemini {model_name}: no candidates")
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    print(f"⚠️ Gemini {model_name}: no parts in response")
                    continue

                reply = parts[0].get("text", "").strip()
                if not reply:
                    continue

                if len(reply) > 800:
                    reply = reply[:797] + "..."

                print(f"✅ Gemini {model_name} javob berdi: {reply[:50]}...")
                return reply

        except httpx.TimeoutException:
            print(f"⚠️ Gemini {model_name}: timeout (12s)")
            continue
        except Exception as e:
            print(f"⚠️ Gemini {model_name} xatolik: {e}")
            continue

    print("⚠️ Barcha Gemini modellari ishlamadi")
    return None
