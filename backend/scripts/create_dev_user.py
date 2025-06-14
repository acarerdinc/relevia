#!/usr/bin/env python3
"""
Create a development user for local testing
Usage: python scripts/create_dev_user.py
"""
import asyncio
import sys
from pathlib import Path
from getpass import getpass

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from db.database import AsyncSessionLocal
from db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_dev_user():
    """Create a development user interactively"""
    print("Create Development User")
    print("-" * 30)
    
    email = input("Email [dev@example.com]: ").strip() or "dev@example.com"
    username = input("Username [developer]: ").strip() or "developer"
    password = getpass("Password [devpass123]: ").strip() or "devpass123"
    
    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"\n❌ User with email {email} already exists!")
            update = input("Update password? (y/N): ").lower() == 'y'
            if update:
                existing_user.hashed_password = pwd_context.hash(password)
                await session.commit()
                print("✅ Password updated!")
            return
        
        # Create new user
        hashed_password = pwd_context.hash(password)
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=True
        )
        
        session.add(new_user)
        await session.commit()
        
        print(f"\n✅ User created successfully!")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}")

if __name__ == "__main__":
    print("Note: Make sure DATABASE_URL is set in your .env file\n")
    try:
        asyncio.run(create_dev_user())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. DATABASE_URL is set in .env")
        print("2. Database is running")
        print("3. Tables exist (run: alembic upgrade head)")
        sys.exit(1)