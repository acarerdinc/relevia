from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from db.database import engine
from db.models import Base
from passlib.context import CryptContext
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/init-database-setup-2024")
async def init_database():
    """Initialize database - REMOVE THIS ENDPOINT AFTER USE"""
    
    # Security check - require special token
    init_token = os.environ.get("INIT_TOKEN", "")
    if not init_token or init_token != "init-relevia-2024-secure":
        return {"error": "Invalid initialization token"}
    
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Insert test users
        async with engine.connect() as conn:
            # Check if users exist
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            
            if count > 0:
                return {"message": f"Database already has {count} users", "initialized": False}
            
            # Test users
            test_users = [
                {
                    "email": "info@acarerdinc.com",
                    "full_name": "Acar Erdinc",
                    "password": "fenapass1",
                    "is_active": True,
                    "is_superuser": True
                },
                {
                    "email": "ogulcancelik@gmail.com", 
                    "full_name": "Ogulcan Celik",
                    "password": "ordekzeze1",
                    "is_active": True,
                    "is_superuser": False
                },
                {
                    "email": "begumcitamak@gmail.com",
                    "full_name": "Begum Citamak", 
                    "password": "zazapass1",
                    "is_active": True,
                    "is_superuser": False
                }
            ]
            
            # Insert users
            for user_data in test_users:
                hashed_password = pwd_context.hash(user_data["password"])
                
                await conn.execute(
                    text("""
                        INSERT INTO users (email, full_name, hashed_password, is_active, is_superuser)
                        VALUES (:email, :full_name, :hashed_password, :is_active, :is_superuser)
                    """),
                    {
                        "email": user_data["email"],
                        "full_name": user_data["full_name"],
                        "hashed_password": hashed_password,
                        "is_active": user_data["is_active"],
                        "is_superuser": user_data["is_superuser"]
                    }
                )
            
            await conn.commit()
            
            # Verify
            result = await conn.execute(text("SELECT email FROM users"))
            users = [u[0] for u in result.fetchall()]
            
            return {
                "message": "Database initialized successfully",
                "users_created": len(test_users),
                "users_in_db": users,
                "initialized": True
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")