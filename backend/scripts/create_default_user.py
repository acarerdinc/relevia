"""
Create a default user for the MVP
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine
from db.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_default_user():
    """Create a default user for testing"""
    async with AsyncSession(engine) as session:
        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.id == 1))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("Default user already exists!")
            print(f"User: {existing_user.username} ({existing_user.email})")
            return
        
        # Create default user
        hashed_password = pwd_context.hash("demo123")
        user = User(
            id=1,
            email="demo@relevia.ai",
            username="demo_user",
            hashed_password=hashed_password,
            is_active=True
        )
        
        session.add(user)
        await session.commit()
        print("✅ Default user created successfully!")
        print(f"Email: demo@relevia.ai")
        print(f"Username: demo_user")
        print(f"Password: demo123")

if __name__ == "__main__":
    asyncio.run(create_default_user())