from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from core.config import settings

# Configure database URL and engine options
database_url = settings.DATABASE_URL

engine_kwargs = {
    "echo": False if database_url.startswith("postgresql") else True,
}

# For Supabase transaction pooler, use special configuration
if "pooler.supabase.com:6543" in database_url:
    # CRITICAL: Disable pool_pre_ping as it causes prepared statement issues with pgbouncer
    engine_kwargs["pool_pre_ping"] = False
    # Use NullPool to prevent connection reuse
    engine_kwargs["poolclass"] = NullPool
    # Disable prepared statements completely
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,  # Disable prepared statements
        "server_settings": {
            "jit": "off"
        },
        "command_timeout": 60
    }
else:
    # For direct connections, use pool_pre_ping
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