"""
Direct database utilities for authentication to bypass pgbouncer issues
"""
import asyncpg
from core.config import settings
from core.logging_config import logger


async def get_user_by_email(email: str):
    """
    Get user by email using direct asyncpg connection
    This bypasses SQLAlchemy to avoid prepared statement issues with pgbouncer
    """
    try:
        # Parse the database URL to get connection parameters
        database_url = settings.DATABASE_URL
        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Create a direct connection
        conn = await asyncpg.connect(database_url)
        
        try:
            # Execute query without prepared statements
            row = await conn.fetchrow(
                "SELECT id, username, email, hashed_password FROM users WHERE email = $1 LIMIT 1",
                email
            )
            return row
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Direct database error getting user {email}: {str(e)}")
        return None