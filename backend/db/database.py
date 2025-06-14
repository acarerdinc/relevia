from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings

# Configure database URL and engine options
database_url = settings.DATABASE_URL

# Check if we're using Turso/libsql
is_turso = database_url.startswith("libsql://") or "turso.io" in database_url

Base = declarative_base()

if is_turso:
    # Use Turso adapter for sync-to-async operations
    from .turso_adapter import get_turso_session
    
    async def get_db():
        async for session in get_turso_session(database_url):
            yield session
    
    # Create a dummy engine for compatibility
    engine = None
else:
    # Use standard async engine for SQLite/PostgreSQL
    engine_kwargs = {
        "echo": False,  # Disable SQL logging for production
    }
    
    # For PostgreSQL connections, use pool_pre_ping
    if database_url.startswith("postgresql"):
        engine_kwargs["pool_pre_ping"] = True
    
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