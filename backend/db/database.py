from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Configure database URL and engine options
database_url = settings.DATABASE_URL

# For Supabase transaction pooler, modify the URL to work with pgbouncer
if "pooler.supabase.com:6543" in database_url:
    # Add prepare_threshold=0 to disable prepared statements
    if "?" in database_url:
        database_url += "&prepare_threshold=0"
    else:
        database_url += "?prepare_threshold=0"

engine_kwargs = {
    "echo": False if database_url.startswith("postgresql") else True,
    "pool_pre_ping": True,  # Test connections before using them
}

# For Supabase transaction pooler, use special configuration
if "pooler.supabase.com:6543" in database_url:
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
    # Disable prepared statements at the connection level
    engine_kwargs["connect_args"] = {
        "server_settings": {"jit": "off"},
        "prepare_threshold": 0,  # Disable prepared statements
        "command_timeout": 60
    }

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