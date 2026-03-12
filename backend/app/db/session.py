"""
Async SQLAlchemy engine and session factory.

Provides a reusable async session maker bound to the PostgreSQL
database configured in settings.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Conditionally add SSL args for PostgreSQL/Neon, but not for SQLite
connect_args = {}
if settings.DATABASE_URL.startswith(("postgresql", "postgresql+asyncpg")):
    connect_args["ssl"] = "require"

# Create the async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Session factory — produces AsyncSession instances
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
