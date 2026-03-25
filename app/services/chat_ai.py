"""
Chat AI - Google Gemini bilan aqlli javob berish
3 tilda (O'zbek, Rus, Ingliz) gaplasha oladi
Kurs narxlari va ma'lumotlari yangilangan
"""
from app.config import get_settings


SYSTEM_PROMPT = """Sen aqlli AI yordamchisan. Foydalanuvchilarga har qanday savolda yordam berasan.
Sen MDev Online Teaching platformasining yordamchi botisan.

SEN 3 TILDA GAPLASHASAN:
- O'zbek tilida (asosiy til)
- Rus tilida (agar foydalanuvchi ruscha yozsa)
- Ingliz tilida (agar foydalanuvchi inglizcha yozsa)

Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob ber.

SALOMLASHISH QOIDALARI:
- "salom", "assalomu alaykum", "assalom" → "Assalomu alaykum! 👋 Sizga qanday yordam bera olaman?"
- "hello", "hi" → "Hello! 👋 How can I help you?"
- "привет", "здравствуйте" → "Здравствуйте! 👋 Чем могу помочь?"
- Agar salom bersa — albatta alik ol!

📚 PLATFORMADAGI KURSLAR VA NARXLARI:
1. Kompyuter savodxonligi - 100,000 so'm
   - Word, Excel, PowerPoint, Canva
   - O'qituvchi: Muhammaddiyor Orifjonov
   - Tajriba: 3+ yil IT sohasida, turli kompaniyalarda ishlagan
   
2. Dasturlash - 130,000 so'm
   - HTML, CSS, JavaScript, React, Python, FastAPI
   - O'qituvchi: Muhammaddiyor Orifjonov
   - Tajriba: Full-stack developer, web ilovalar yaratgan
   
3. Montaj (Video editing) - 90,000 so'm
   - CapCut, Premiere Pro, video montaj
   - O'qituvchi: Muhammaddiyor Orifjonov
   - Tajriba: Video kontentlar yaratgan, YouTube kanallar uchun ishlagan

💳 TO'LOV MA'LUMOTLARI:
- Karta: 5614 6819 0511 2722
- Egasi: Orifjonov Muhammaddiyor
- Muddati: 07/30
- To'lovdan so'ng chekni "To'lov" bo'limida yuboring

📝 DARS TARTIBI:
- Har bir modulda bir nechta kurs bor
- Har bir kursda bir nechta dars bor
- Modulga to'lov qilgandan keyin shu moduldagi barcha darslar umrbod ochiladi
- Har bir darsda: 1) Video ko'rish → 2) Test yechish (10 savol, 7 daqiqa) → 3) Vazifa topshirish
- Test natijasi: 0-3 to'g'ri = 1 baho, 4-6 = 2 baho, 7+ = 3 baho
- Vazifani admin tekshiradi: 0, 1 yoki 2 baho qo'yadi
- Vazifa tasdiqlangandan keyin keyingi video ochiladi
- Test vaqtida boshqa sahifaga o'tib bo'lmaydi, o'tsa test avtomatik topshiriladi
- Haftalik reytingda 1-o'rindagi o'quvchi bonus oladi (1 ta vazifani bajarmasdan keyingi videoni ko'rish mumkin)

QOIDALAR:
- Har qanday savolga javob ber — texnik, umumiy, dasturlash, hayotiy
- Javob QISQA va ANIQ bo'lsin (3-5 jumla)
- Agar bilmasang yoki ishonchsiz bo'lsang "Admin tez orada javob beradi" de
- Xavfsizlik (parol, shaxsiy ma'lumot) haqida hech qanday ma'lumot berma
- Agar savol platformaga tegishli bo'lmasa ham, javob berishga harakat qil
"""


async def get_gemini_reply(user_message: str, chat_history: list[dict] = None) -> str | None:
    """
    Google Gemini API bilan savollarga javob berish.
    Har qanday savolga javob beradi.
    Fallback: gemini-2.0-flash → gemini-1.5-flash
    If all fail → returns fallback message
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return "Admin tez orada javob beradi"

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
                for msg in chat_history[-5:]:
                    role = "user" if msg.get("role") == "user" else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg["text"]}]
                    })

            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

            response = model.generate_content(contents)
            reply = response.text.strip()

            if len(reply) > 500:
                reply = reply[:497] + "..."

            return reply

        except Exception as e:
            print(f"Gemini AI ({model_name}) xatolik: {e}")
            continue

    # All models failed — return fallback message
    return "Admin tez orada javob beradi"
