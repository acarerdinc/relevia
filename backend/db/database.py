from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
import os

# Configure database URL and engine options
database_url = settings.DATABASE_URL

Base = declarative_base()

# Configure engine based on database type
is_postgresql = database_url.startswith("postgresql")
is_turso = database_url.startswith("libsql") or database_url.startswith("turso")
is_vercel = os.environ.get("VERCEL", "0") == "1"

if is_postgresql and is_vercel:
    # Use NullPool for Vercel + PostgreSQL (with PgBouncer)
    from sqlalchemy.pool import NullPool
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
        "poolclass": NullPool,  # Let PgBouncer handle pooling
        "connect_args": {
            "statement_cache_size": 0,  # Disable prepared statements for pgbouncer
        }
    }
else:
    # Standard configuration for local development
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True if is_postgresql else False,
    }

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()