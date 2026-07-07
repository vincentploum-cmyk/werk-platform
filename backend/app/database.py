"""Database session management for Werk Platform."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.db_models import Base

logger = logging.getLogger(__name__)

# Async engine for PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency: get an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup (development only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_schema():
    """Lightweight idempotent migrations for existing databases (no Alembic needed).

    Creates any new tables and adds columns introduced after the initial schema.
    Safe to run on every startup.
    """
    # create_all is checkfirst by default → only creates missing tables (e.g. app_settings).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    statements = [
        "ALTER TABLE agents ADD COLUMN project_id UUID",  # SOW-deployed, project-scoped agents
        "ALTER TABLE artifacts ADD COLUMN content TEXT",  # generated deliverable text
    ]
    for stmt in statements:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
            logger.info(f"Applied migration: {stmt}")
        except Exception:
            # Column already exists (or dialect rejects re-add) — fine, it's idempotent.
            pass


async def close_db():
    """Dispose of the engine on shutdown."""
    await engine.dispose()