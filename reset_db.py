"""Drop all tables and recreate with new schema, then seed initial data"""
import asyncio
from sqlalchemy import text
from app.database import engine, Base
from app.models import *  # Import all models so Base knows about them


async def reset():
    print("⚠️  Barcha jadvallarni o'chirish...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    print("✅ Jadvallar o'chirildi")

    print("🔨 Yangi jadvallarni yaratish...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Yangi jadvallar yaratildi")

    # Seed data with real YouTube video lessons
    from app.database import AsyncSessionLocal
    from app.models.course import Module, Course, Lesson

    async with AsyncSessionLocal() as db:
        # === 3 MODULLAR ===
        m1 = Module(name="Kompyuter savodxonligi", slug="kompyuter-savodxonligi",
                    description="Word, Excel, PowerPoint, Canva va boshqa dasturlarni o'rganish", price=80000, order=1)
        m2 = Module(name="Dasturlash", slug="dasturlash",
                    description="Frontend: HTML, CSS, JS, React. Backend: Python, FastAPI, Node.js", price=100000, order=2)
        m3 = Module(name="Montaj", slug="montaj",
                    description="CapCut, Premiere Pro va video montaj san'ati", price=80000, order=3)
        db.add_all([m1, m2, m3])
        await db.flush()

        # === KURSLAR ===
        c1 = Course(module_id=m1.id, name="Kompyuter savodxonligi kursi", slug="kompyuter-kurs",
                    description="Word, Excel, Canva dasturlari bo'yicha to'liq kurs", order=1)
        c2 = Course(module_id=m2.id, name="Dasturlash kursi", slug="dasturlash-kurs",
                    description="Full Stack dasturlash: HTML dan React gacha", order=1)
        c3 = Course(module_id=m3.id, name="Montaj kursi", slug="montaj-kurs",
                    description="Professional video montaj", order=1)
        db.add_all([c1, c2, c3])
        await db.flush()

        # === DARSLAR (foydalanuvchi bergan YouTube linklar) ===
        # Modul 1: Kompyuter savodxonligi
        l1 = Lesson(
            course_id=c1.id, title="Kompyuter savodxonligi kirish darsi", slug="komp-kirish", order=1,
            is_free=True,
            video_url="https://www.youtube.com/embed/GOU2_-8o1rI",
            description="Bu darsda kompyuter savodxonligi haqida asosiy tushunchalar bilan tanishasiz."
        )
        l2 = Lesson(
            course_id=c1.id, title="Word va Excel dasturlari", slug="word-excel", order=2,
            is_free=False,
            video_url="https://www.youtube.com/embed/Z9KrYaTM5wA",
            description="Microsoft Word va Excel dasturlarida ishlashni o'rganasiz."
        )

        # Modul 2: Dasturlash
        l3 = Lesson(
            course_id=c2.id, title="HTML asoslari - Web sahifa yaratish", slug="html-asoslar", order=1,
            is_free=True,
            video_url="https://www.youtube.com/embed/0NdDKClb1eQ",
            description="HTML tilining asosiy teglari va tuzilishi. Birinchi web sahifangizni yaratish."
        )
        l4 = Lesson(
            course_id=c2.id, title="CSS bilan dizayn qilish", slug="css-asoslar", order=2,
            is_free=False,
            video_url="https://www.youtube.com/embed/_f8cpjAz0sw",
            description="CSS yordamida web sahifangizni chiroyli qilishni o'rganasiz."
        )

        # Modul 3: Montaj
        l5 = Lesson(
            course_id=c3.id, title="Video montaj asoslari", slug="montaj-kirish", order=1,
            is_free=True,
            video_url="https://www.youtube.com/embed/erltNa-PeYw",
            description="Video montaj nima va qanday qilinadi. CapCut dasturi bilan tanishish."
        )
        l6 = Lesson(
            course_id=c3.id, title="Professional montaj texnikalari", slug="pro-montaj", order=2,
            is_free=False,
            video_url="https://www.youtube.com/embed/55PTTFGfp3I",
            description="Effektlar, transitions va professional montaj texnikalari."
        )

        db.add_all([l1, l2, l3, l4, l5, l6])
        await db.commit()

    print("✅ Boshlang'ich ma'lumotlar yaratildi!")
    print("📋 Modullar: Kompyuter savodxonligi (80k), Dasturlash (100k), Montaj (80k)")
    print("📹 6 ta dars qo'shildi (har modulga 2 ta, birinchisi bepul)")
    print("🎉 Tayyor! Serverni qayta ishga tushiring.")


if __name__ == "__main__":
    asyncio.run(reset())
