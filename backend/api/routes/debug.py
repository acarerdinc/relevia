"""Debug routes for testing database connection"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import get_db
from core.logging_config import logger
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/debug/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all users in database - for debugging only"""
    try:
        from db.models import User
        from sqlalchemy import select
        
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        return {
            "total_users": len(users),
            "users": [
                {
                    "email": user.email,
                    "username": user.username,
                    "hash_prefix": user.hashed_password[:20] + "..." if user.hashed_password else None
                }
                for user in users
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/debug/db-test")
async def test_database(db: AsyncSession = Depends(get_db)):
    """Test database connection"""
    try:
        logger.info("Testing database connection")
        
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
            emails = [row[0] for row in rows]  # Always use index for raw SQL results
            
            from core.config import settings
            db_type = "PostgreSQL" if settings.DATABASE_URL.startswith("postgresql") else "SQLite"
            
            return {
                "status": "ok", 
                "database_type": db_type,
                "database_url_prefix": settings.DATABASE_URL[:30] + "...",
                "users_count": count,
                "user_emails": emails
            }
        except Exception as e:
            logger.error(f"Users table error: {str(e)}")
            from core.config import settings
            import os
            db_type = "PostgreSQL" if settings.DATABASE_URL.startswith("postgresql") else "SQLite"
            
            return {
                "status": "error", 
                "message": "Users table not found", 
                "error": str(e),
                "database_type": db_type,
                "database_url_prefix": settings.DATABASE_URL[:30] + "...",
                "is_vercel": os.environ.get("VERCEL", "0"),
                "has_postgres_url": bool(os.environ.get("POSTGRES_URL")),
                "has_database_url": bool(os.environ.get("DATABASE_URL"))
            }
            
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/debug/verify-password")
async def verify_password_test():
    """Test bcrypt password verification"""
    test_password = "zarzara111"
    
    # Generate a new hash for this password
    new_hash = pwd_context.hash(test_password)
    
    # Test verification with the new hash
    verify_result = pwd_context.verify(test_password, new_hash)
    
    return {
        "test_password": test_password,
        "generated_hash": new_hash,
        "hash_length": len(new_hash),
        "verification_result": verify_result,
        "hash_prefix": new_hash[:20],
        "message": "This hash should be stored in the database for the user"
    }