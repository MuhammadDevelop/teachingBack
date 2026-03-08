# 🚀 Render.com ga Deploy Qilish

## 📋 1-qadam: GitHub ga push qilish

```bash
git add .
git commit -m "Render deploy tayyor"
git push origin main
```

## ☁️ 2-qadam: Render.com da Web Service yaratish

1. [render.com](https://render.com) ga kiring
2. **New → Web Service** bosing
3. GitHub repo ni ulang
4. Sozlashlar:
   - **Name:** `mdev-teaching-api`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## 🔐 3-qadam: Environment Variables sozlash

Render dashboard → **Environment** tab da quyidagilarni qo'shing:

| Kalit | Qiymat |
|-------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://neondb_owner:...@....neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | Tasodifiy maxfiy kalit (masalan: `openssl rand -hex 32`) |
| `TELEGRAM_BOT_TOKEN` | Bot tokeningiz |
| `FRONTEND_URL` | Frontend URL (masalan: `https://your-frontend.vercel.app`) |
| `ADMIN_PHONE` | `998889810206` |
| `CARD_NUMBER` | `5614 6819 0511 2722` |
| `CARD_HOLDER` | `Orifjonov Muhammaddiyor` |
| `CARD_EXPIRY` | `07/30` |
| `GEMINI_API_KEY` | Google Gemini API kalitingiz |
| `PORT` | `8000` |

> [!IMPORTANT]
> `RENDER_EXTERNAL_URL` — bu Render.com **avtomatik** beradi, o'zingiz qo'shishingiz **shart emas**!

## 🚀 4-qadam: Deploy!

- **Manual Deploy** yoki **Auto-Deploy** yoqing
- Render avtomatik `requirements.txt` o'rnatadi va server ishga tushadi
- Tekshirish: `https://mdev-teaching-api.onrender.com/health` → `{"status": "healthy"}`
- API docs: `https://mdev-teaching-api.onrender.com/docs`

## ⚡ 24/7 Ishlash (Bepul rejim)

Bepul rejada server 15 daqiqa so'rov bo'lmasa "uxlaydi".

**Yechim:** [UptimeRobot](https://uptimerobot.com) dan monitoring qo'shing:
1. Ro'yxatdan o'ting
2. **Add New Monitor → HTTP(s)** tanlang
3. **URL:** `https://mdev-teaching-api.onrender.com/health`
4. **Interval:** 5 daqiqa

## 🧪 Lokal Test

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```
