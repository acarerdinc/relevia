from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings
from core.logging_config import logger
import os
import asyncpg
import time
from contextlib import asynccontextmanager

# Configure database URL and engine options
database_url = settings.DATABASE_URL

# Check if we're using Supabase pooler URL (port 6543)
is_pooler_url = ":6543" in database_url

Base = declarative_base()

# Configure engine based on database type
is_postgresql = database_url.startswith("postgresql") or database_url.startswith("postgres")
is_turso = database_url.startswith("libsql") or database_url.startswith("turso")
is_vercel = os.environ.get("VERCEL", "0") == "1"

logger.info(f"Database configuration: postgresql={is_postgresql}, pooler={is_pooler_url}, vercel={is_vercel}")

if is_postgresql and (is_vercel or is_pooler_url):
    # Optimized configuration for Supabase/Supavisor + Vercel
    from sqlalchemy.pool import NullPool
    
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": False,  # Disable for serverless
        "poolclass": NullPool,  # Let Supavisor handle pooling
        "connect_args": {
            # Supavisor/pgbouncer transaction mode optimizations
            "server_settings": {
                "jit": "off",
                "application_name": "relevia_backend"
            },
            "command_timeout": 5,  # Short timeout for serverless
            "prepared_statement_cache_size": 0,  # Disable for transaction mode
            "statement_cache_size": 0,
            # Additional optimizations
            "max_cached_statement_lifetime": 0,
            "max_cacheable_statement_size": 0,
        }
    }
    logger.info("Using optimized serverless configuration for Supabase/Supavisor")
else:
    # Standard configuration for local development
    engine_kwargs = {
        "echo": False,  # False for production
        "pool_pre_ping": True if is_postgresql else False,
    }

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@asynccontextmanager
async def get_db_context():
    """Context manager version of get_db for better control"""
    session = AsyncSessionLocal()
    start_time = time.time()
    
    try:
        yield session
        await session.commit()
        logger.debug(f"DB session committed in {(time.time() - start_time)*1000:.2f}ms")
    except Exception as e:
        await session.rollback()
        logger.error(f"DB session rolled back after {(time.time() - start_time)*1000:.2f}ms: {e}")
        raise
    finally:
        # Quick close for serverless
        if is_vercel or is_pooler_url:
            try:
                # Try quick close with timeout
                import asyncio
                await asyncio.wait_for(session.close(), timeout=0.5)
            except asyncio.TimeoutError:
                # If close times out, just continue
                logger.warning("Session close timed out, continuing...")
        else:
            await session.close()

async def get_db():
    """FastAPI dependency for database sessions"""
    async with get_db_context() as session:
        yield session

# Direct connection helper for critical operations
@asynccontextmanager
async def get_direct_connection():
    """Get a direct database connection bypassing SQLAlchemy for critical operations"""
    if not is_postgresql:
        # For non-PostgreSQL, just use regular session
        async with get_db_context() as session:
            yield session
        return
    
    conn = None
    try:
        # Use asyncpg directly for PostgreSQL
        conn = await asyncpg.connect(
            database_url,
            timeout=5,
            command_timeout=5,
            statement_cache_size=0
        )
        
        # Create a minimal wrapper to match session interface
        class DirectConnection:
            def __init__(self, conn):
                self._conn = conn
            
            async def execute(self, query, *args):
                if hasattr(query, 'text'):
                    # SQLAlchemy text query
                    return await self._conn.fetch(str(query), *args)
                return await self._conn.fetch(query, *args)
            
            async def commit(self):
                pass  # No-op for direct connection
            
            async def rollback(self):
                pass  # No-op for direct connection
        
        yield DirectConnection(conn)
        
    finally:
        if conn:
            try:
                await asyncio.wait_for(conn.close(), timeout=1)
            except:
                pass  # Ignore close errors