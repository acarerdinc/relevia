from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Configure database URL for transaction pooling if needed
database_url = settings.DATABASE_URL
if "pooler.supabase.com:6543" in database_url and "statement_cache_size" not in database_url:
    # Add statement_cache_size=0 for transaction pooler
    if "?" in database_url:
        database_url += "&statement_cache_size=0"
    else:
        database_url += "?statement_cache_size=0"

# Use echo=False in production to reduce logs
is_production = database_url.startswith("postgresql")
engine = create_async_engine(
    database_url,
    echo=not is_production,
)

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