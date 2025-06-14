"""Synchronous database adapter for Turso/libsql"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from core.config import settings
import asyncio
from typing import AsyncGenerator

# Configure database URL and engine options
database_url = settings.DATABASE_URL

# Check if we're using Turso (libsql)
is_turso = database_url.startswith("libsql://")

if is_turso:
    # Use sync engine for Turso
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Wrap sync session in async context
    async def get_db() -> AsyncGenerator[Session, None]:
        """Get database session (sync wrapped in async for Turso)"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
else:
    # Use async engine for SQLite
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """Get database session (async for SQLite)"""
        async with AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

Base = declarative_base()