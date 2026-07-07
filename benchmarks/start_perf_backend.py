import uvicorn
import unittest.mock as mock
import fakeredis.aioredis
import os
import sqlalchemy.ext.asyncio

# Override environment variables for performance testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./perf_werk.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

original_create_async_engine = sqlalchemy.ext.asyncio.create_async_engine

def patched_create_async_engine(url, **kwargs):
    if url.startswith("sqlite"):
        # Remove PostgreSQL specific arguments
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
    return original_create_async_engine(url, **kwargs)

# Mock aioredis and create_async_engine before importing app
with mock.patch("redis.asyncio.from_url", side_effect=fakeredis.aioredis.FakeRedis), \
     mock.patch("sqlalchemy.ext.asyncio.create_async_engine", side_effect=patched_create_async_engine):
    from app.main import app
    from app.database import init_db
    
    @app.on_event("startup")
    async def startup_event():
        await init_db()

    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000)
