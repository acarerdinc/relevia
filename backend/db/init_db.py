"""
Initialize database with users and root topic
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine, Base
from db.models import User, Topic, UserSkillProgress
from api.routes.auth import get_password_hash
from datetime import datetime

async def init_database():
    """Initialize database with required data"""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as db:
        # Check if users already exist
        from sqlalchemy import select
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Database already initialized")
            return
        
        # Create users
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
            db.add(new_user)
        
        await db.commit()
        
        # Create root AI topic
        ai_topic = Topic(
            name="Artificial Intelligence",
            description="The study and development of computer systems able to perform tasks that typically require human intelligence",
            parent_id=None,
            difficulty_min=1,
            difficulty_max=10
        )
        db.add(ai_topic)
        await db.commit()
        await db.refresh(ai_topic)
        
        # Create initial skill progress for user 1
        skill_progress = UserSkillProgress(
            user_id=1,
            topic_id=ai_topic.id,
            skill_level=0.0,
            confidence=0.0,
            questions_answered=0,
            correct_answers=0,
            mastery_level="novice",
            current_mastery_level="novice",
            mastery_questions_answered={"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0},
            is_unlocked=True,
            unlocked_at=datetime.now(),
            proficiency_threshold_met=False
        )
        db.add(skill_progress)
        await db.commit()
        
        print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_database())