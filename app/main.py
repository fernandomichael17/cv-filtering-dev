"""FastAPI application entry point.

- CORS enabled for development
- Static files served from /static
- Tables created on startup
- E5-small semantic model loaded on startup
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_tables
from app.routes import jobs_router, filtering_router, candidates_router
from app.routes.portal_simulator import router as portal_router
from core.utils.logger import setup_logging

# Configure logging using core setup
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Mengelola siklus hidup aplikasi FastAPI pada startup dan shutdown.

    Startup:
    1. Membuat tabel database milik cv-filtering jika belum ada.
    2. Memuat model semantic matcher (E5-small) untuk pencocokan semantik.

    Parameter:
        app (FastAPI): Instansi aplikasi FastAPI.

    Return:
        None
    """
    logger.info("Creating tables (if not exist)...")
    await create_tables()

    logger.info("Loading semantic fallback model on startup...")
    try:
        from core.filtering.semantic_matcher import semantic_matcher
        semantic_matcher.initialize()
        logger.info("Semantic fallback model ready.")
    except Exception as e:
        logger.error("Failed to load semantic fallback model: %s", e)
        logger.warning("Semantic fallback matching will be unavailable!")

    logger.info("Application ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.APP_TITLE,
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(jobs_router)
app.include_router(filtering_router)

app.include_router(candidates_router)
app.include_router(portal_router)

# Static files — serve index.html at /
app.mount("/", StaticFiles(directory="static", html=True), name="static")
