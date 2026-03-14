"""
FastAPI Application Factory — main entry point.
Creates the FastAPI app with lifespan management (DB table creation,
ChromaDB initialization), mounts participant and organizer routers
under /api/v1/, and configures CORS middleware.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.organizer import router as organizer_router, events_router
from app.api.participant import router as participant_router, join_router
from app.core.rag import get_chroma_client
from app.db.models import Base
from app.db.session import engine, async_session_factory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Suppress noisy polling endpoints from uvicorn access logs
# ---------------------------------------------------------------------------

class _PollingSilencer(logging.Filter):
    """Filter out frequent polling GET requests that clutter the terminal."""

    _NOISY_SUFFIXES = ("/logs", "/priority_queue", "/unresolved_queries", "/resolved_tickets")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # uvicorn access log format: '<ip> - "<METHOD> <path> ..." <status>'
        if "GET" in msg and any(suffix in msg for suffix in self._NOISY_SUFFIXES):
            return False  # suppress
        return True


logging.getLogger("uvicorn.access").addFilter(_PollingSilencer())


async def _apply_schema_patches() -> None:
    """
    Apply lightweight schema patches for existing deployments.

    create_all() creates missing tables but does not add new columns to
    existing tables.
    """
    async with engine.begin() as conn:
        dialect = conn.dialect.name

        if dialect == "postgresql":
            await conn.execute(text(
                """
                ALTER TABLE IF EXISTS email_logs
                ADD COLUMN IF NOT EXISTS category_reports JSONB DEFAULT '[]'::jsonb;
                """
            ))
            await conn.execute(text(
                """
                ALTER TABLE IF EXISTS unresolved_queries
                ADD COLUMN IF NOT EXISTS organizer_answer TEXT DEFAULT NULL;
                """
            ))
        elif dialect == "sqlite":
            result = await conn.execute(text("PRAGMA table_info(email_logs)"))
            existing_columns = {row[1] for row in result.fetchall()}
            if "category_reports" not in existing_columns:
                await conn.execute(text(
                    "ALTER TABLE email_logs ADD COLUMN category_reports JSON DEFAULT '[]'"
                ))


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
      - Verify PostgreSQL (Neon) connection is reachable.
      - Create all database tables (if they don't exist).
      - Initialize the ChromaDB client and collection.

    On shutdown:
      - Dispose of the database engine connection pool.
    """
    logger.info("🚀 Starting Event Command Center...")

    # ── Verify Neon/PostgreSQL connection ────────────────────────────────────
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ PostgreSQL (Neon) connection verified.")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("   Check your DATABASE_URL in .env and that Neon is reachable.")
        raise  # Fail fast — don't start the server with a broken DB

    # ── Create database tables ───────────────────────────────────────────────
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified.")
    except Exception as e:
        logger.error(f"❌ Table creation failed: {e}")
        raise

    # ── Apply schema patches for existing deployments ───────────────────────
    try:
        await _apply_schema_patches()
        logger.info("✅ Schema patch check complete.")
    except Exception as e:
        logger.error(f"❌ Schema patch failed: {e}")
        raise

    # ── Initialize ChromaDB ──────────────────────────────────────────────────
    try:
        client = get_chroma_client()
        logger.info(f"✅ ChromaDB initialized. Collections: {client.list_collections()}")
    except Exception as e:
        logger.warning(f"⚠️  ChromaDB initialization failed: {e}")
        logger.warning("   Q&A bot will be unavailable until ChromaDB is fixed.")
        # Not raising here — app can still run without ChromaDB for other agents

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down Event Command Center...")
    await engine.dispose()
    logger.info("✅ Database connections closed.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Autonomous Event Command Center",
    description=(
        "A scalable, multi-tenant backend for managing large-scale event "
        "logistics with AI-powered autonomous agents. Every operation is "
        "scoped by event_id for complete data isolation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers under /api/v1/
app.include_router(auth_router, prefix="/api/v1")
app.include_router(participant_router, prefix="/api/v1")
app.include_router(join_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(organizer_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health_check():
    """Basic liveness check — confirms the server is running."""
    return {
        "status": "healthy",
        "service": "Autonomous Event Command Center",
        "version": "1.0.0",
    }


@app.get("/health/db", tags=["System"])
async def db_health_check():
    """
    Deep health check — verifies live PostgreSQL (Neon) connectivity.
    Useful for debugging connection issues after deployment.
    """
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "PostgreSQL (Neon)",
            "connection": "ok",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "PostgreSQL (Neon)",
            "connection": "failed",
            "error": str(e),
        }