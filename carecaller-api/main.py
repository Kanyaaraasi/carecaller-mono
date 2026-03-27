"""CareCaller API — FastAPI backend that bridges the UI to the voice agent's brain."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api import calls, patients, questions
from config import get_settings
from db.connection import close_db, get_session, init_db
from db.seed import seed_db
from services.livekit_service import close as close_livekit

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("carecaller-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + seed. Shutdown: close DB."""
    settings = get_settings()
    await init_db(settings.db_path)

    async for session in get_session():
        await seed_db(session)

    logger.info("API ready")
    yield
    await close_livekit()
    await close_db()


app = FastAPI(title="CareCaller API", version="0.1.0", lifespan=lifespan)

app.include_router(patients.router)
app.include_router(questions.router)
app.include_router(calls.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
