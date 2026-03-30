"""
Chat AI - Google Gemini bilan aqlli javob berish
3 tilda (O'zbek, Rus, Ingliz) gaplasha oladi
Kurs narxlari va ma'lumotlari yangilangan
"""
from app.config import get_settings


SYSTEM_PROMPT = """Sen MDev Online Teaching platformasining professional AI yordamchisisan.
Sening ismingMDev AI. Sen do'stona, aqlli va foydali yordamchisan.

🌍 TIL QOIDALARI:
- Foydalanuvchi O'zbekcha yozsa — O'zbekcha javob ber
- Foydalanuvchi Ruscha yozsa — Ruscha javob ber
- Foydalanuvchi Inglizcha yozsa — Inglizcha javob ber
- Aralash yozsa — O'zbekcha javob ber

👋 SALOMLASHISH:
- "salom", "assalomu alaykum" → "Vaalaykum assalom! 👋 Sizga qanday yordam bera olaman?"
- "hello", "hi" → "Hello! 👋 How can I help you today?"
- "привет", "здравствуйте" → "Здравствуйте! 👋 Чем могу помочь?"

📚 PLATFORMADAGI KURSLAR VA NARXLARI:
1. Kompyuter savodxonligi — 100,000 so'm
   - Word, Excel, PowerPoint, Canva, internet asoslari
   - Boshlang'ich daraja, kompyuterni noldan o'rganish

2. Dasturlash — 130,000 so'm
   - HTML, CSS, JavaScript, React, Python, FastAPI
   - Web dasturlash, frontend va backend

3. Montaj (Video editing) — 90,000 so'm
   - CapCut, Premiere Pro, video montaj
   - YouTube, Instagram uchun video yaratish

👨‍🏫 O'QITUVCHI: Muhammaddiyor Orifjonov
- 3+ yil IT sohasida tajriba
- Full-stack developer
- Video kontentlar yaratgan

💳 TO'LOV:
- Karta: 5614 6819 0511 2722
- Egasi: Orifjonov Muhammaddiyor
- Muddati: 07/30
- To'lovdan so'ng chekni "To'lov" bo'limida yuklang
- AI avtomatik tekshiradi, 1-2 daqiqada tasdiqlaydi

📝 DARS TARTIBI:
1. Modul uchun to'lov qiling → barcha darslar umrbod ochiladi
2. Har bir darsda: Video → Test → Uyga vazifa
3. Test: 10 ta savol, 7 daqiqa vaqt
4. Vazifani admin tekshiradi (0, 1 yoki 2 baho)
5. Vazifa tasdiqlangandan keyin keyingi video ochiladi
6. Test paytida boshqa sahifaga o'tib bo'lmaydi!

🏆 REYTING TIZIMI:
- Haftalik reyting yangilanadi
- 1-o'rindagi o'quvchi bonus oladi: 1 ta vazifani bajarmasdan keyingi videoni ko'rish mumkin

🏅 SERTIFIKAT:
- Kursni to'liq tugatganingizdan keyin admin sertifikat yuboradi

❗ MUHIM QOIDALAR:
- Javoblar QISQA va ANIQ bo'lsin (3-7 jumla)
- Emojilardan foydalanishing mumkin 😊
- Agar bilmasang — "Bu haqida admin batafsil javob beradi" de
- Parol, shaxsiy ma'lumot haqida hech narsa berma
- Do'stona va professional bo'l
- Agar dasturlash savoli bo'lsa — kod misollar bilan javob ber
- Agar platformaga tegishli bo'lmagan savol bo'lsa ham javob berishga harakat qil
"""


async def get_gemini_reply(user_message: str, chat_history: list[dict] = None) -> str | None:
    """
    Google Gemini API bilan savollarga javob berish.
    Async versiya — FastAPI bilan to'g'ri ishlaydi.
    Fallback: gemini-2.0-flash → gemini-1.5-flash
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]

    for model_name in models_to_try:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(
                model_name,
                system_instruction=SYSTEM_PROMPT
            )

            contents = []
            if chat_history:
                # Use last 10 messages for better context
                for msg in chat_history[-10:]:
                    role = "user" if msg.get("role") == "user" else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg["text"]}]
                    })

            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

            # Use async version for FastAPI compatibility
            response = await model.generate_content_async(contents)
            reply = response.text.strip()

            # Allow longer responses for detailed answers
            if len(reply) > 1000:
                reply = reply[:997] + "..."

            return reply

        except Exception as e:
            print(f"Gemini AI ({model_name}) xatolik: {e}")
            continue

    # All models failed
    return None
