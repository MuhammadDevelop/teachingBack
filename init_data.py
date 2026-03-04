"""Seed initial data: 3 modules with their courses and first free lesson each"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, Base, engine
from app.models import Module, Course, Lesson
from app.config import get_settings


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    settings = get_settings()

    async with AsyncSessionLocal() as db:
        # Check if data exists
        result = await db.execute(select(Module))
        if result.scalars().first():
            print("Data already exists")
            return

        # Modules (3 ta modul)
        m1 = Module(
            name="Kompyuter savodxonligi",
            slug="kompyuter-savodxonligi",
            description="Word, Excel, PowerPoint, Canva va boshqa dasturlarni o'rganish",
            price=80000,
            order=1
        )
        m2 = Module(
            name="Dasturlash",
            slug="dasturlash",
            description="Frontend: HTML, CSS, JS, React. Backend: Python, FastAPI, Node.js, SQL",
            price=100000,
            order=2
        )
        m3 = Module(
            name="Montaj",
            slug="montaj",
            description="CapCut, Premiere Pro va video montaj san'ati",
            price=80000,
            order=3
        )
        db.add_all([m1, m2, m3])
        await db.flush()

        # Courses (har modulda 1 ta kurs)
        c1 = Course(
            module_id=m1.id,
            name="Kompyuter savodxonligi kursi",
            slug="kompyuter-kurs",
            description="Word, Excel, Canva dasturlari bo'yicha to'liq kurs",
            order=1
        )
        c2 = Course(
            module_id=m2.id,
            name="Dasturlash kursi",
            slug="dasturlash-kurs",
            description="Full Stack dasturlash: HTML dan Node.js gacha",
            order=1
        )
        c3 = Course(
            module_id=m3.id,
            name="Montaj kursi",
            slug="montaj-kurs",
            description="Professional video montaj",
            order=1
        )
        db.add_all([c1, c2, c3])
        await db.flush()

        # First free lesson for each course
        l1 = Lesson(
            course_id=c1.id,
            title="Kirish - Word asoslari",
            slug="kirish-word",
            order=1,
            is_free=True,
            video_url="https://example.com/word-kirish.mp4",
            description="Word dasturi bilan tanishish"
        )
        l2 = Lesson(
            course_id=c2.id,
            title="Kirish - HTML asoslari",
            slug="kirish-html",
            order=1,
            is_free=True,
            video_url="https://example.com/html-kirish.mp4",
            description="HTML bilan tanishish"
        )
        l3 = Lesson(
            course_id=c3.id,
            title="Kirish - CapCut tanishish",
            slug="kirish-capcut",
            order=1,
            is_free=True,
            video_url="https://example.com/capcut-kirish.mp4",
            description="CapCut dasturi bilan tanishish"
        )
        db.add_all([l1, l2, l3])
        await db.commit()
        print("✅ Initial data created successfully!")
        print(f"📋 Modules: Kompyuter savodxonligi (80,000), Dasturlash (100,000), Montaj (80,000)")
        print(f"👤 Admin phone: {settings.admin_phone}")


if __name__ == "__main__":
    asyncio.run(init())
