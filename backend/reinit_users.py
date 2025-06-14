"""
Reinitialize users in the database with correct passwords
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from db.models import User, Base
from api.routes.auth import get_password_hash
from core.config import settings

async def reinit_users():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        # Delete existing users
        result = await session.execute(select(User))
        existing_users = result.scalars().all()
        for user in existing_users:
            await session.delete(user)
        await session.commit()
        print(f"Deleted {len(existing_users)} existing users")
        
        # Create new users with correct passwords
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
        
        for user_data in users:
            hashed_password = get_password_hash(user_data["password"])
            new_user = User(
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=hashed_password,
                is_active=True
            )
            session.add(new_user)
            print(f"Created user: {user_data['email']}")
        
        await session.commit()
        print("All users created successfully!")
        
        # Verify users
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        print(f"\nVerification: Found {len(all_users)} users in database")
        for user in all_users:
            print(f"- {user.email} (active: {user.is_active})")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reinit_users())