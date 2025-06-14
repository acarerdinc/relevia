"""
Script to set up specific user accounts
"""
import asyncio
from sqlalchemy import delete
from db.database import engine, get_db
from db.models import User
from api.routes.auth import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession

async def setup_users():
    async with AsyncSession(engine) as db:
        try:
            # First, delete all existing users
            print("🧹 Removing existing users...")
            await db.execute(delete(User))
            await db.commit()
            print("✅ Existing users removed")
            
            # User accounts to create
            users = [
                {
                    "email": "info@acarerdinc.com",
                    "username": "acarerdinc",
                    "password": "fenapass1"
                },
                {
                    "email": "ogulcancelik@gmail.com",
                    "username": "ogulcancelik",
                    "password": "ordekzeze1"
                },
                {
                    "email": "begumcitamak@gmail.com",
                    "username": "begumcitamak",
                    "password": "zazapass1"
                }
            ]
            
            # Create new users
            print("\n📝 Creating new user accounts...")
            for user_data in users:
                hashed_password = get_password_hash(user_data["password"])
                new_user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=hashed_password,
                    is_active=True
                )
                db.add(new_user)
                print(f"✅ Created user: {user_data['email']}")
            
            await db.commit()
            print("\n🎉 All user accounts created successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(setup_users())