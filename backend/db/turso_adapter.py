"""Turso database adapter that wraps sync libsql in async context"""
import asyncio
from functools import partial
from typing import Any, AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import threading

# Thread-local storage for database connections
_thread_local = threading.local()

def get_sync_engine(database_url: str):
    """Get or create a sync engine for the current thread"""
    if not hasattr(_thread_local, 'engine'):
        # Create engine with StaticPool to avoid connection issues
        _thread_local.engine = create_engine(
            database_url,
            connect_args={},
            poolclass=StaticPool,
            echo=False
        )
    return _thread_local.engine

def get_sync_session(database_url: str) -> Session:
    """Get a sync database session"""
    engine = get_sync_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

class AsyncTursoSession:
    """Async wrapper for Turso sync session"""
    
    def __init__(self, sync_session: Session):
        self.sync_session = sync_session
        self._loop = asyncio.get_event_loop()
    
    async def execute(self, *args, **kwargs):
        """Execute query in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            partial(self.sync_session.execute, *args, **kwargs)
        )
    
    async def commit(self):
        """Commit in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            self.sync_session.commit
        )
    
    async def rollback(self):
        """Rollback in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            self.sync_session.rollback
        )
    
    async def close(self):
        """Close in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            self.sync_session.close
        )
    
    def add(self, instance):
        """Add instance (sync operation)"""
        return self.sync_session.add(instance)
    
    async def flush(self):
        """Flush in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            self.sync_session.flush
        )
    
    async def refresh(self, instance):
        """Refresh in thread pool"""
        return await self._loop.run_in_executor(
            None, 
            partial(self.sync_session.refresh, instance)
        )
    
    # Add query method for compatibility
    def query(self, *args, **kwargs):
        """Query (returns sync query object)"""
        return self.sync_session.query(*args, **kwargs)
    
    # Make it work with async context manager
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        await self.close()

async def get_turso_session(database_url: str) -> AsyncGenerator[AsyncTursoSession, None]:
    """Get async Turso database session"""
    sync_session = get_sync_session(database_url)
    async_session = AsyncTursoSession(sync_session)
    try:
        yield async_session
    finally:
        await async_session.close()