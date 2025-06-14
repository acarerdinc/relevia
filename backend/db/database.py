from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Configure database URL and engine options
database_url = settings.DATABASE_URL
engine_kwargs = {"echo": False if database_url.startswith("postgresql") else True}

# For Supabase transaction pooler, disable prepared statements
if "pooler.supabase.com:6543" in database_url:
    engine_kwargs["connect_args"] = {"statement_cache_size": 0}

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