"""
Initialize Turso database with tables and test users
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from passlib.context import CryptContext
from db.models import Base, User, Topic
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_database():
    # Get Turso credentials from environment
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Please set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables")
        return
    
    # Create database URL with auth token
    database_url = f"{turso_url}?authToken={turso_token}"
    
    print(f"🔗 Connecting to Turso database...")
    
    # Create engine
    engine = create_async_engine(database_url, echo=True)
    
    # Create all tables
    async with engine.begin() as conn:
        print("📋 Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Check if users already exist
        from sqlalchemy import select
        result = await session.execute(select(User))
        existing_users = result.scalars().all()
        
        if existing_users:
            print("ℹ️  Users already exist in database. Skipping user creation.")
        else:
            print("👥 Creating test users...")
            
            # Test users
            test_users = [
                {
                    "email": "info@acarerdinc.com",
                    "username": "acarerdinc",
                    "password": "fenapass1"
                },
                {
                    "email": "ogulcancelik@gmail.com",
                    "username": "ogulcan",
                    "password": "ordekzeze1"
                },
                {
                    "email": "begumcitamak@gmail.com",
                    "username": "begum",
                    "password": "zazapass1"
                }
            ]
            
            for user_data in test_users:
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=pwd_context.hash(user_data["password"])
                )
                session.add(user)
                print(f"✅ Created user: {user_data['email']}")
            
            await session.commit()
        
        # Add a root topic if it doesn't exist
        result = await session.execute(select(Topic).where(Topic.name == "Technology"))
        root_topic = result.scalar_one_or_none()
        
        if not root_topic:
            print("📚 Creating root topic...")
            root_topic = Topic(
                name="Technology",
                description="Root topic for technology learning",
                parent_id=None
            )
            session.add(root_topic)
            await session.commit()
            print("✅ Created root topic: Technology")
        else:
            print("ℹ️  Root topic already exists.")
    
    await engine.dispose()
    print("🎉 Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_database())