"""
Database Connection Manager with retry logic and optimized pooling for quiz sessions
"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    OperationalError, 
    DatabaseError, 
    TimeoutError as SQLTimeoutError,
    InterfaceError,
    DisconnectionError
)
try:
    from asyncpg.exceptions import (
        ConnectionDoesNotExistError,
        TooManyConnectionsError,
        PostgresConnectionError
    )
except ImportError:
    # Fallback for different asyncpg versions
    ConnectionDoesNotExistError = Exception
    TooManyConnectionsError = Exception
    PostgresConnectionError = Exception

from core.logging_config import logger
from db.database import get_db_context, AsyncSessionLocal, is_vercel, is_pooler_url

T = TypeVar('T')

class ConnectionManager:
    """Manages database connections with retry logic and optimizations"""
    
    def __init__(self):
        self.max_retries = 3
        self.base_delay = 0.1  # 100ms
        self.max_delay = 2.0   # 2 seconds
        self.jitter_factor = 0.1
        
        # Connection pool stats
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.retry_count = 0
        
    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable"""
        retryable_errors = (
            # SQLAlchemy errors
            OperationalError,
            TimeoutError,
            SQLTimeoutError,
            InterfaceError,
            DisconnectionError,
            
            # asyncpg errors
            ConnectionDoesNotExistError,
            TooManyConnectionsError,
            PostgresConnectionError,
            
            # Python errors
            asyncio.TimeoutError,
            ConnectionError,
            OSError
        )
        
        if isinstance(error, retryable_errors):
            return True
            
        # Check for specific error messages
        error_msg = str(error).lower()
        retryable_messages = [
            "connection reset",
            "connection closed",
            "connection lost",
            "connection timeout",
            "too many connections",
            "prepared statement",
            "server closed the connection",
            "connection is closed",
            "cannot perform operation",
            "pool timeout"
        ]
        
        return any(msg in error_msg for msg in retryable_messages)
    
    def _calculate_backoff(self, retry_attempt: int) -> float:
        """Calculate exponential backoff with jitter"""
        delay = min(self.base_delay * (2 ** retry_attempt), self.max_delay)
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        return delay + jitter
    
    @asynccontextmanager
    async def get_session(self, timeout: Optional[float] = None):
        """Get a database session with retry logic"""
        self.connection_attempts += 1
        retry_attempt = 0
        last_error = None
        
        while retry_attempt <= self.max_retries:
            try:
                # Use the optimized get_db_context
                async with get_db_context() as session:
                    self.successful_connections += 1
                    yield session
                    return
                    
            except Exception as e:
                last_error = e
                
                if not self._is_retryable_error(e) or retry_attempt >= self.max_retries:
                    self.failed_connections += 1
                    logger.error(f"Non-retryable database error after {retry_attempt} retries: {e}")
                    raise
                
                self.retry_count += 1
                backoff_time = self._calculate_backoff(retry_attempt)
                logger.warning(
                    f"Retryable database error (attempt {retry_attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {backoff_time:.2f}s..."
                )
                
                await asyncio.sleep(backoff_time)
                retry_attempt += 1
        
        self.failed_connections += 1
        raise last_error
    
    async def execute_with_retry(
        self, 
        func: Callable[[AsyncSession], Any],
        timeout: Optional[float] = None
    ) -> T:
        """Execute a database operation with retry logic"""
        async with self.get_session(timeout=timeout) as session:
            if timeout:
                return await asyncio.wait_for(func(session), timeout=timeout)
            return await func(session)
    
    def with_retry(self, timeout: Optional[float] = None):
        """Decorator for adding retry logic to database operations"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract session from args/kwargs if present
                session = None
                for arg in args:
                    if isinstance(arg, AsyncSession):
                        session = arg
                        break
                if not session:
                    session = kwargs.get('db') or kwargs.get('session')
                
                if session:
                    # If session is already provided, just execute the function
                    return await func(*args, **kwargs)
                
                # Otherwise, get a new session with retry
                async with self.get_session(timeout=timeout) as session:
                    # Inject session into kwargs
                    kwargs['db'] = session
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_stats(self) -> dict:
        """Get connection pool statistics"""
        success_rate = (
            self.successful_connections / self.connection_attempts 
            if self.connection_attempts > 0 else 0
        )
        
        return {
            "total_attempts": self.connection_attempts,
            "successful": self.successful_connections,
            "failed": self.failed_connections,
            "retries": self.retry_count,
            "success_rate": success_rate,
            "average_retries_per_failure": (
                self.retry_count / self.failed_connections 
                if self.failed_connections > 0 else 0
            )
        }
    
    async def health_check(self) -> dict:
        """Perform a health check on database connectivity"""
        start_time = time.time()
        
        try:
            async with self.get_session(timeout=5.0) as session:
                # Simple query to verify connection
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                
                latency = (time.time() - start_time) * 1000  # ms
                
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "connection_type": "pooler" if is_pooler_url else "direct",
                    "environment": "vercel" if is_vercel else "local",
                    "stats": self.get_stats()
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__,
                "stats": self.get_stats()
            }


# Global connection manager instance
connection_manager = ConnectionManager()

# Convenience functions
get_session = connection_manager.get_session
execute_with_retry = connection_manager.execute_with_retry
with_retry = connection_manager.with_retry