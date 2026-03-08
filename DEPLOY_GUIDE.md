# 🚀 Deploy va 24/7 Ishlash Yo'riqnomasi

## 📋 Kerakli sozlashlar

### `.env` fayliga qo'shish kerak:
```
GEMINI_API_KEY=sizning_gemini_api_kalitingiz
```

**Gemini API kalitini olish:** [Google AI Studio](https://aistudio.google.com/apikey) dan bepul oling.

---

## 🤖 Telegram Bot ni Ishga Tushirish

### Lokal (Development)
Bot lokal kompyuterda **polling** rejimida ishlaydi:

```bash
# 1. Paketlarni o'rnatish
pip install -r requirements.txt

# 2. Bot ni alohida terminalda ishga tushirish
python run_bot.py

# 3. Server ni boshqa terminalda ishga tushirish
uvicorn app.main:app --reload --port 8000
```

### Production (Render.com)
Bot Render.com da **webhook** rejimida ishlaydi (alohida bot jarayoni kerak emas):

1. Server o'zi webhook orqali Telegram dan xabar oladi
2. `RENDER_EXTERNAL_URL` avtomatik sozlanadi
3. `/webhook/telegram` endpoint orqali bot ishlaydi

---

## ☁️ Render.com ga Deploy Qilish (24/7)

### 1-qadam: GitHub ga push qilish
```bash
git add .
git commit -m "AI payment verification va chat"
git push origin main
```

### 2-qadam: Render.com da yangi Web Service yaratish
1. [render.com](https://render.com) ga kiring
2. **New → Web Service** bosing
3. GitHub repo ni ulang
4. Sozlashlar:
   - **Name:** `mdev-teaching-api`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3-qadam: Environment Variables sozlash
Render dashboard → Environment tab da quyidagilarni qo'shing:

| Kalit | Qiymat |
|-------|--------|
| `DATABASE_URL` | PostgreSQL URL (Neon/Supabase) |
| `SECRET_KEY` | Tasodifiy maxfiy kalit |
| `TELEGRAM_BOT_TOKEN` | Bot tokeningiz |
| `FRONTEND_URL` | Frontend URL |
| `ADMIN_PHONE` | `998889810206` |
| `CARD_NUMBER` | `5614 6819 0511 2722` |
| `CARD_HOLDER` | `Orifjonov Muhammaddiyor` |
| `CARD_EXPIRY` | `07/30` |
| `GEMINI_API_KEY` | Google Gemini API kaliti |
| `RENDER_EXTERNAL_URL` | Render avtomatik beradi |

### 4-qadam: Deploy bosing!
- Render avtomatik deploy qiladi
- Server 24/7 ishlaydi
- Har bir push da avtomatik qayta deploy bo'ladi

---

## ⚡ 24/7 Ishlash Uchun

### Render Free Tier
- Bepul rejada server 15 daqiqa so'rov bo'lmasa "uxlaydi"
- **Yechim:** [UptimeRobot](https://uptimerobot.com) dan bepul monitoring qo'shing
  1. Ro'yxatdan o'ting
  2. **Add New Monitor → HTTP(s)** tanlang
  3. **URL:** `https://sizning-app.onrender.com/health`
  4. **Interval:** 5 daqiqa
  - Bu har 5 daqiqada server ga so'rov yuborib, uxlamasligini ta'minlaydi

### Render Paid Tier ($7/oy)
- Server hech qachon uxlamaydi
- Tezroq deploy
- Custom domain

---

## 🧪 Lokal Test Qilish

```bash
# 1. Virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Paketlarni o'rnatish
pip install -r requirements.txt

# 3. .env faylni sozlash
# DATABASE_URL, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN

# 4. Server ishga tushirish
uvicorn app.main:app --reload --port 8000

# 5. API dokumentatsiyani ko'rish
# http://localhost:8000/docs

# 6. Bot ni alohida ishga tushirish (ixtiyoriy)
python run_bot.py
```

---

## 📡 Admin Select API Endpointlar

Frontend admin panelda select/dropdown uchun:

```
GET /admin/select/modules   → [{id, name, price}]
GET /admin/select/courses   → [{id, name, module_id, module_name}]  ?module_id=1
GET /admin/select/lessons   → [{id, title, course_id, course_name, has_test, has_homework, has_game}]  ?course_id=1
GET /admin/select/students  → [{id, name, phone}]
```

**Misol (Frontend):**
```javascript
// Modul tanlash
const modules = await fetch('/admin/select/modules').then(r => r.json());
// <select> ga qo'shish
modules.forEach(m => {
  const option = document.createElement('option');
  option.value = m.id;
  option.textContent = `${m.name} (${m.price} so'm)`;
  selectElement.appendChild(option);
});
```
