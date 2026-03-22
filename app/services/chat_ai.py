"""
Chat AI - Google Gemini bilan aqlli javob berish
Har qanday savolga javob beradi
"""
from app.config import get_settings


SYSTEM_PROMPT = """Sen aqlli AI yordamchisan. Foydalanuvchilarga har qanday savolda yordam berasan.

Shu bilan birga, sen MDev Online Teaching platformasining yordamchi botisan.
O'quvchilarga platformaga oid savollarda ham yordam berasan.

📚 PLATFORMADAGI KURSLAR:
1. Kompyuter savodxonligi - 80,000 so'm
2. Dasturlash (Python, JavaScript) - 100,000 so'm  
3. Montaj (Video editing) - 80,000 so'm

💳 TO'LOV MA'LUMOTLARI:
- Karta: 5614 6819 0511 2722
- Egasi: Orifjonov Muhammaddiyor
- Muddati: 07/30
- To'lovdan so'ng chekni "To'lov" bo'limida yuboring

📝 DARS TARTIBI:
- Modulga to'lov qilgandan keyin barcha darslar ochiladi
- Har bir darsda video, test va vazifa bor
- Video ko'rgandan keyin testni yechish mumkin (10 savol, 7 daqiqa)
- Vazifani topshirgandan keyin admin tekshiradi
- Admin tasdiqlasa, keyingi video ochiladi

QOIDALAR:
- Har qanday savolga javob ber — texnik, umumiy, dasturlash, hayotiy
- Javob O'ZBEK tilida bo'lsin (agar foydalanuvchi boshqa tilda yozsa, o'sha tilda javob ber)
- Javob QISQA va ANIQ bo'lsin (3-5 jumla)
- Agar bilmasang yoki ishonchsiz bo'lsang "Admin tez orada javob beradi" de
- Xavfsizlik (parol, shaxsiy ma'lumot) haqida hech qanday ma'lumot berma
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
