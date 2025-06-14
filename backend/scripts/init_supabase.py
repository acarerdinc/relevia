#!/usr/bin/env python3
"""
Initialize Supabase PostgreSQL database with tables and test users
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.supabase_config import get_async_engine
from db.models import Base
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_database():
    """Initialize database with tables and test users"""
    engine = get_async_engine()
    
    try:
        # Create all tables
        print("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created successfully")
        
        # Insert test users
        async with engine.connect() as conn:
            # Check if users already exist
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            
            if count > 0:
                print(f"ℹ Database already has {count} users")
                return
            
            print("Creating test users...")
            
            # Test users data
            test_users = [
                {
                    "email": "info@acarerdinc.com",
                    "username": "acarerdinc",
                    "password": "fenapass1",
                    "is_active": True
                },
                {
                    "email": "ogulcancelik@gmail.com", 
                    "username": "ogulcancelik",
                    "password": "ordekzeze1",
                    "is_active": True
                },
                {
                    "email": "begumcitamak@gmail.com",
                    "username": "begumcitamak", 
                    "password": "zazapass1",
                    "is_active": True
                }
            ]
            
            # Insert users
            for user_data in test_users:
                hashed_password = pwd_context.hash(user_data["password"])
                
                await conn.execute(
                    text("""
                        INSERT INTO users (email, username, hashed_password, is_active)
                        VALUES (:email, :username, :hashed_password, :is_active)
                    """),
                    {
                        "email": user_data["email"],
                        "username": user_data["username"],
                        "hashed_password": hashed_password,
                        "is_active": user_data["is_active"]
                    }
                )
                print(f"✓ Created user: {user_data['email']}")
            
            await conn.commit()
            print("\n✓ All test users created successfully!")
            
            # Verify users
            result = await conn.execute(text("SELECT email FROM users"))
            users = result.fetchall()
            print(f"\nUsers in database: {[u[0] for u in users]}")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("Initializing Supabase PostgreSQL database...")
    print(f"Database URL configured: {bool(os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL'))}")
    asyncio.run(init_database())