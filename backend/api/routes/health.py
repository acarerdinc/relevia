from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.database import get_db
from db.models import User
import os

router = APIRouter()

@router.get("/")
@router.get("")
async def health_check():
    return {"status": "healthy", "service": "relevia-api"}

@router.get("/db-check")
async def database_check(db: AsyncSession = Depends(get_db)):
    """Check database connectivity and initialization"""
    try:
        # Check if we can connect to the database
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        # Check if users table exists and has data
        user_count_result = await db.execute(select(User))
        users = user_count_result.scalars().all()
        user_count = len(users)
        
        # Get database URL (masked for security)
        db_url = os.environ.get("POSTGRES_URL", "sqlite")
        if "sqlite" in db_url:
            db_type = "SQLite"
            if os.environ.get("VERCEL") == "1":
                db_location = "/tmp/relevia.db"
            else:
                db_location = "./relevia.db"
        else:
            db_type = "PostgreSQL"
            db_location = "external"
        
        return {
            "status": "connected",
            "database_type": db_type,
            "database_location": db_location,
            "is_vercel": os.environ.get("VERCEL") == "1",
            "users_count": user_count,
            "users": [{
                "id": user.id,
                "username": user.username,
                "email": user.email
            } for user in users]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "is_vercel": os.environ.get("VERCEL") == "1"
        }