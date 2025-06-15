from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
import os
import asyncpg

# Configure database URL and engine options
database_url = settings.DATABASE_URL

Base = declarative_base()

# Configure engine based on database type
is_postgresql = database_url.startswith("postgresql")
is_turso = database_url.startswith("libsql") or database_url.startswith("turso")
is_vercel = os.environ.get("VERCEL", "0") == "1"

if is_postgresql and is_vercel:
    # Use NullPool for Vercel + PostgreSQL (with PgBouncer/Supavisor)
    from sqlalchemy.pool import NullPool
    from uuid import uuid4
    
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
        "poolclass": NullPool,  # Let PgBouncer handle pooling
        "connect_args": {
            "server_settings": {
                "jit": "off"
            },
            "command_timeout": 10,  # Reduce timeout to fail fast
            "prepared_statement_cache_size": 0,  # Disable prepared statements for pgbouncer
            "statement_cache_size": 0,  # Also try this variant
            # Generate unique prepared statement names to avoid conflicts
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
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
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        # Don't wait for close to complete on Vercel
        if is_vercel:
            import asyncio
            # Fire and forget - don't wait for close
            asyncio.create_task(session.close())
        else:
            await session.close()

# Raw asyncpg connection for login to avoid prepared statement issues
_raw_pool = None

async def get_raw_pool():
    global _raw_pool
    if _raw_pool is None and is_postgresql and is_vercel:
        # Extract connection details from DATABASE_URL
        import re
        from core.logging_config import logger
        
        logger.info(f"Creating raw pool for URL prefix: {database_url[:30]}...")
        
        # Try both postgresql:// and postgres:// patterns
        match = re.match(r'postgres(?:ql)?://([^:]+):([^@]+)@([^/]+)/(.+)', database_url)
        if match:
            user, password, host, database = match.groups()
            try:
                _raw_pool = await asyncpg.create_pool(
                    host=host.split(':')[0],
                    port=int(host.split(':')[1]) if ':' in host else 5432,
                    user=user,
                    password=password,
                    database=database.split('?')[0],
                    min_size=1,
                    max_size=2,
                    command_timeout=60,
                    statement_cache_size=0  # Disable prepared statements for pgbouncer
                )
                logger.info("Raw asyncpg pool created successfully")
            except Exception as e:
                logger.error(f"Failed to create raw pool: {e}")
        else:
            logger.error(f"Could not parse database URL")
    return _raw_pool