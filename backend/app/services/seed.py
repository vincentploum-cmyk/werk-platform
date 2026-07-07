"""Ensure the global agent roster contains every role in the catalog.

Runs at startup so databases provisioned before a role existed (e.g. PMO, Release) get the
new template agents added without a manual migration.
"""

import logging

from sqlalchemy import select

from app.database import async_session_factory
from app.models.db_models import Agent
from app.services.sow_service import ROLE_CATALOG

logger = logging.getLogger(__name__)


async def ensure_default_agents() -> None:
    async with async_session_factory() as db:
        existing = (
            await db.execute(select(Agent).where(Agent.project_id.is_(None)))
        ).scalars().all()
        have = {a.role for a in existing}
        added = []
        for role, cat in ROLE_CATALOG.items():
            if role not in have:
                db.add(Agent(
                    name=cat["name"], type=cat["type"], role=role,
                    capabilities=cat["capabilities"], project_id=None, status="idle",
                ))
                added.append(role)
        if added:
            await db.commit()
            logger.info(f"Seeded missing template agents: {', '.join(added)}")
