"""Tailored Resume API."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from database.connection import init_db
from api.auth import router as auth_router
from api.resume import router as resume_router
from api.job import router as job_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    Path(get_settings().upload_dir).mkdir(parents=True, exist_ok=True)
    yield
    # shutdown if needed


app = FastAPI(
    title="Tailored Resume API",
    description="ATS-optimized resume generation",
    version="1.0.0",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(resume_router)
app.include_router(job_router)


@app.get("/health")
def health():
    return {"status": "ok"}


