"""
Chat AI - Google Gemini bilan aqlli javob berish
O'qitish platformasi haqida savolga javob beradi
"""
from app.config import get_settings


SYSTEM_PROMPT = """Sen MDev Online Teaching platformasining yordamchi AI botisan. 
O'quvchilarga yordam berasan. Quyidagi ma'lumotlarga asoslanib javob ber:

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
- Har bir kursda bir nechta modullar bor
- Har bir darsda video, test (10 ta savol), vazifa va o'yin bor
- Videoni ko'rgandan so'ng testni 2 soat ichida yechish kerak
- Test kamida 7/10 to'g'ri javob bo'lsa o'tiladi

🏆 REYTING VA BONUSLAR:
- Har hafta eng yaxshi 3 ta o'quvchiga bonus ball beriladi
- 1-o'rin: 25 ball, 2-o'rin: 15 ball, 3-o'rin: 10 ball
- Bonus balllar imtihonda ishlatiladi

📋 IMTIHON:
- Har bir kurs oxirida imtihon bor
- Maksimal 100 ball, o'tish balli 60
- Muvaffaqiyatli o'tganlarga sertifikat beriladi

QOIDALAR:
- Javob QISQA va ANIQ bo'lsin (3-4 jumla)
- O'zbek tilida javob ber
- Agar bilmasang "Admin tez orada javob beradi" de
- Texnik savollar uchun "Admin bilan bog'laning" de
- Xavfsizlik (parol, shaxsiy ma'lumot) haqida hech qanday ma'lumot berma
"""


async def get_gemini_reply(user_message: str, chat_history: list[dict] = None) -> str | None:
    """
    Google Gemini API bilan savollarga javob berish.
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

    return None
