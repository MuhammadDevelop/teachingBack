"""
To'lov chekini AI bilan tekshirish - Google Gemini Vision API
Orifjonov Muhammaddiyor nomiga tushganmi va summani tekshiradi
"""
import json
import re
from app.config import get_settings


async def verify_payment_check(image_base64: str, expected_amount: int = 0) -> dict:
    """
    Chek rasmini Gemini Vision API bilan tahlil qilish.
    
    Returns:
        {
            "is_valid": bool,
            "recipient_name": str,
            "amount": int,
            "timestamp": str,
            "confidence": float,
            "ai_comment": str
        }
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return {
            "is_valid": False,
            "recipient_name": "",
            "amount": 0,
            "timestamp": "",
            "confidence": 0.0,
            "ai_comment": "GEMINI_API_KEY sozlanmagan"
        }

    try:
        import google.generativeai as genai
        
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Base64 dan rasm yaratish
        if image_base64.startswith("data:"):
            # data:image/jpeg;base64,... formatidan base64 ni ajratish
            parts = image_base64.split(",", 1)
            mime_type = parts[0].split(":")[1].split(";")[0]
            raw_base64 = parts[1]
        else:
            mime_type = "image/jpeg"
            raw_base64 = image_base64

        image_part = {
            "mime_type": mime_type,
            "data": raw_base64
        }

        prompt = f"""Bu to'lov cheki/screenshot rasmini tahlil qil. 
Quyidagi ma'lumotlarni aniqla va JSON formatda javob ber:

1. "recipient_name" - Pul kimga o'tkazilgan (qabul qiluvchi nomi)
2. "amount" - Qancha pul o'tkazilgan (faqat raqam, so'mda)
3. "timestamp" - O'tkazma vaqti (agar ko'rinsa)
4. "is_payment_screenshot" - Bu haqiqiy to'lov chekimi (true/false)

Muhim: Asosan "Orifjonov Muhammaddiyor" yoki "ORIFJONOV MUHAMMADDIYOR" nomiga pul tushdimi tekshir.
Kutilgan summa: {expected_amount} so'm

FAQAT JSON formatda javob ber, boshqa hech narsa yozma:
{{"recipient_name": "...", "amount": 0, "timestamp": "...", "is_payment_screenshot": true/false}}
"""

        response = model.generate_content([prompt, image_part])
        response_text = response.text.strip()

        # JSON ni parse qilish
        # Markdown code block ichida bo'lishi mumkin
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)

        recipient = result.get("recipient_name", "").upper()
        is_correct_recipient = "ORIFJONOV" in recipient and "MUHAMMADDIYOR" in recipient
        amount = int(result.get("amount", 0))
        is_payment = result.get("is_payment_screenshot", False)

        # Summani tekshirish (agar kutilgan summa berilgan bo'lsa)
        amount_ok = True
        if expected_amount > 0:
            # 10% farq ruxsat etiladi
            amount_ok = abs(amount - expected_amount) <= expected_amount * 0.1

        is_valid = is_correct_recipient and is_payment and amount_ok
        confidence = 0.9 if is_valid else 0.3

        comment_parts = []
        if is_correct_recipient:
            comment_parts.append(f"✅ Qabul qiluvchi: {result.get('recipient_name', '?')}")
        else:
            comment_parts.append(f"❌ Qabul qiluvchi noto'g'ri: {result.get('recipient_name', '?')}")
        
        comment_parts.append(f"💰 Summa: {amount:,} so'm")
        
        if result.get("timestamp"):
            comment_parts.append(f"🕐 Vaqt: {result.get('timestamp')}")
        
        if not is_payment:
            comment_parts.append("⚠️ Bu to'lov cheki emas deb aniqlandi")

        return {
            "is_valid": is_valid,
            "recipient_name": result.get("recipient_name", ""),
            "amount": amount,
            "timestamp": result.get("timestamp", ""),
            "confidence": confidence,
            "ai_comment": "\n".join(comment_parts)
        }

    except Exception as e:
        return {
            "is_valid": False,
            "recipient_name": "",
            "amount": 0,
            "timestamp": "",
            "confidence": 0.0,
            "ai_comment": f"AI tekshirish xatoligi: {str(e)}"
        }
