from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings

# Configure database URL and engine options
database_url = settings.DATABASE_URL

engine_kwargs = {
    "echo": False,  # Disable SQL logging for production
}

# For Turso/libsql, no special configuration needed
# For PostgreSQL connections, use pool_pre_ping
if database_url.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()