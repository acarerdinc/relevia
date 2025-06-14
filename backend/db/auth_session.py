"""
Special database session for authentication to avoid pgbouncer prepared statement issues
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings

# Create a separate engine for auth with no connection pooling
auth_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # No connection pooling
    connect_args={
        "statement_cache_size": 0,  # Disable prepared statements
        "prepared_statement_cache_size": 0,
        "server_settings": {
            "jit": "off"
        },
    }
)

# Create session factory for auth
AuthSessionLocal = sessionmaker(
    auth_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_auth_db():
    """Get a fresh database session for authentication"""
    async with AuthSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()