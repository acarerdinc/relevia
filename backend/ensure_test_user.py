#!/usr/bin/env python3
"""
Ensure test user exists in database
"""
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import User

async def ensure_test_user():
    async with AsyncSessionLocal() as db:
        # Check if user with ID 1 exists
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create test user
            test_user = User(
                id=1,
                email="test@example.com",
                username="testuser",
                hashed_password="$2b$12$dummy_hashed_password",  # Not for real auth
                is_active=True
            )
            db.add(test_user)
            await db.commit()
            print("✅ Created test user with ID 1")
        else:
            print(f"✅ Test user already exists: {user.username}")

if __name__ == "__main__":
    asyncio.run(ensure_test_user())