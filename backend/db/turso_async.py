"""Async wrapper for Turso database using sync_to_async"""
from typing import Optional, Any, Dict, List
import asyncio
from functools import partial
from .turso_sync import get_turso_db
from core.logging_config import logger

class AsyncTursoSession:
    """Async session wrapper for Turso that behaves like SQLAlchemy AsyncSession"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.sync_db = get_turso_db(database_url)
        self._loop = None
    
    async def execute(self, statement, params=None):
        """Execute a statement asynchronously"""
        # Convert SQLAlchemy statement to SQL string
        if hasattr(statement, 'compile'):
            # It's a SQLAlchemy query
            compiled = statement.compile()
            query_str = str(compiled)
            # Extract parameters from compiled query
            if params is None and hasattr(compiled, 'params'):
                params = compiled.params
        else:
            # It's a text query
            query_str = str(statement)
        
        logger.debug(f"Executing query: {query_str}")
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            partial(self.sync_db.execute_query, query_str, params)
        )
        
        # Return a result-like object
        return AsyncResult(result)
    
    async def commit(self):
        """Commit (no-op for Turso as we auto-commit)"""
        pass
    
    async def rollback(self):
        """Rollback (no-op for Turso)"""
        pass
    
    async def close(self):
        """Close session"""
        pass
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        raise StopAsyncIteration
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class AsyncResult:
    """Async result wrapper"""
    
    def __init__(self, rows):
        self.rows = rows if rows else []
    
    def scalar(self):
        """Get scalar result"""
        if self.rows and len(self.rows) > 0:
            row = self.rows[0]
            if isinstance(row, tuple) and len(row) > 0:
                return row[0]
            elif isinstance(row, dict):
                return list(row.values())[0] if row else None
        return None
    
    def scalar_one_or_none(self):
        """Get scalar or None"""
        return self.scalar()
    
    def fetchall(self):
        """Fetch all rows"""
        return self.rows
    
    def fetchone(self):
        """Fetch one row"""
        return self.rows[0] if self.rows else None

async def get_turso_session(database_url: str):
    """Get an async Turso session"""
    session = AsyncTursoSession(database_url)
    try:
        yield session
    finally:
        await session.close()