from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.database import get_db
from db.models import User
from db.connection_manager import connection_manager
from core.logging_config import logger
import os
import time

router = APIRouter()

@router.get("/")
@router.get("")
async def health_check():
    return {
        "status": "healthy", 
        "service": "relevia-api",
        "version": "1.0.1",  # Dummy change to trigger deployment
        "deployed_at": "2025-06-14",
        "timestamp": time.time(),
        "environment": os.environ.get("VERCEL", "local")
    }

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

@router.get("/health/db")
async def database_health_check():
    """Database connectivity health check with connection manager"""
    try:
        db_health = await connection_manager.health_check()
        
        # Add additional context
        db_health["connection_pool_stats"] = connection_manager.get_stats()
        
        # Determine overall health status
        if db_health["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=db_health)
        
        return db_health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

@router.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive health check including all subsystems"""
    health_status = {
        "overall": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Basic app health
    health_status["checks"]["app"] = {
        "status": "healthy",
        "environment": os.environ.get("VERCEL", "local"),
        "python_version": os.environ.get("PYTHON_VERSION", "unknown")
    }
    
    # Database health
    try:
        db_health = await connection_manager.health_check()
        health_status["checks"]["database"] = db_health
        
        if db_health["status"] == "unhealthy":
            health_status["overall"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["overall"] = "unhealthy"
    
    # Environment variables check
    required_vars = ["DATABASE_URL", "SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    health_status["checks"]["configuration"] = {
        "status": "healthy" if not missing_vars else "unhealthy",
        "missing_vars": missing_vars
    }
    
    if missing_vars:
        health_status["overall"] = "unhealthy"
    
    # Return appropriate status code
    if health_status["overall"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    elif health_status["overall"] == "degraded":
        # Return 200 with degraded status for partial failures
        return health_status
    
    return health_status