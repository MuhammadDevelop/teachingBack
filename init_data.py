"""Seed initial data: categories and courses with first free lesson each"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, Base, engine
from app.models import Category, Course, Lesson, Video, User
from app.database import get_db


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Categories
        result = await db.execute(select(Category))
        if result.scalars().first():
            print("Data already exists")
            return

        cat1 = Category(name="Kompyuter savodxonligi", slug="kompyuter-savodxonligi", order=1,
                        description="Word, Excel, Canva")
        cat2 = Category(name="Montaj", slug="montaj", order=2, description="CapCut montaj darslari")
        cat3 = Category(name="Dasturlash", slug="dasturlash", order=3,
                        description="Frontend: HTML, CSS, JS, React, Next.js, TypeScript. Backend: Python, FastAPI, Node.js, SQL. Bot darslari")

        db.add_all([cat1, cat2, cat3])
        await db.flush()

        # Courses - Kompyuter 50,000 | Montaj 70,000 | Dasturlash 100,000 (in sum, API uses tiyin: *100)
        c1 = Course(category_id=cat1.id, name="Kompyuter savodxonligi", slug="kompyuter-savodxonligi",
                    description="Word, Excel, Canva", price=5000000, order=1)  # 50,000 sum
        c2 = Course(category_id=cat2.id, name="Montaj darslari", slug="montaj-darslari",
                    description="CapCut orqali montaj", price=7000000, order=1)  # 70,000 sum
        c3 = Course(category_id=cat3.id, name="Dasturlash darslari", slug="dasturlash-darslari",
                    description="Full stack dasturlash", price=10000000, order=1)  # 100,000 sum

        db.add_all([c1, c2, c3])
        await db.flush()

        # First lesson FREE for each course
        l1 = Lesson(course_id=c1.id, title="Kirish - Word asoslari", slug="kirish-word", order=1, is_free=True)
        l2 = Lesson(course_id=c2.id, title="Kirish - CapCut tanishuv", slug="kirish-capcut", order=1, is_free=True)
        l3 = Lesson(course_id=c3.id, title="Kirish - HTML asoslari", slug="kirish-html", order=1, is_free=True)

        db.add_all([l1, l2, l3])
        await db.flush()

        v1 = Video(lesson_id=l1.id, title="Word kirish", video_url="https://example.com/v1.mp4", order=0)
        v2 = Video(lesson_id=l2.id, title="CapCut kirish", video_url="https://example.com/v2.mp4", order=0)
        v3 = Video(lesson_id=l3.id, title="HTML kirish", video_url="https://example.com/v3.mp4", order=0)

        db.add_all([v1, v2, v3])
        await db.commit()
        print("Initial data created successfully!")


if __name__ == "__main__":
    asyncio.run(init())
