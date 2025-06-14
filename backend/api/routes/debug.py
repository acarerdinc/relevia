"""Debug routes for testing database connection"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import get_db, is_turso
from core.logging_config import logger

router = APIRouter()

@router.get("/debug/db-test")
async def test_database(db: AsyncSession = Depends(get_db)):
    """Test database connection"""
    try:
        logger.info(f"Testing database connection. Is Turso: {is_turso}")
        
        # Test basic connection
        result = await db.execute(text("SELECT 1"))
        test_val = result.scalar()
        logger.info(f"Database connection successful, test value: {test_val}")
        
        # Check if users table exists
        try:
            users_result = await db.execute(text("SELECT COUNT(*) as count FROM users"))
            count = users_result.scalar()
            logger.info(f"Users table has {count} users")
            
            # Get user emails
            emails_result = await db.execute(text("SELECT email FROM users"))
            rows = emails_result.fetchall()
            emails = [row[0] if isinstance(row, tuple) else row['email'] for row in rows]
            
            return {
                "status": "ok", 
                "is_turso": is_turso,
                "users_count": count,
                "user_emails": emails
            }
        except Exception as e:
            logger.error(f"Users table error: {str(e)}")
            return {"status": "error", "message": "Users table not found", "error": str(e)}
            
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {"status": "error", "message": str(e)}