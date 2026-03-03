from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, get_db
from app.routers import auth, courses, payments, admin
from app.config import get_settings

app = FastAPI(title="Online Teaching Platform", version="1.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(payments.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {"message": "Online Teaching Platform API", "docs": "/docs"}


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
