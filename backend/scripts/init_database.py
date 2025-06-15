#!/usr/bin/env python3
"""
Initialize database with minimal setup for adaptive learning
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine, Base
from db.models import User, Topic, UserSkillProgress, DynamicTopicUnlock
from datetime import datetime, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_database():
    """Initialize database with minimal data"""
    print("🚀 Initializing database...")
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    
    async with AsyncSession(engine) as session:
        # Check if already initialized
        from sqlalchemy import select
        result = await session.execute(select(Topic))
        if result.first():
            print("ℹ️  Database already initialized")
            # Just make sure root topic is unlocked for user
            topic_result = await session.execute(select(Topic).where(Topic.parent_id == None))
            root_topic = topic_result.scalar_one_or_none()
            if root_topic:
                # Check if already unlocked
                skill_result = await session.execute(
                    select(UserSkillProgress).where(
                        UserSkillProgress.user_id == 1,
                        UserSkillProgress.topic_id == root_topic.id
                    )
                )
                if not skill_result.scalar_one_or_none():
                    # Create skill progress
                    skill_progress = UserSkillProgress(
                        user_id=1,
                        topic_id=root_topic.id,
                        questions_answered=0,
                        correct_answers=0,
                        mastery_level='novice',
                        current_mastery_level='novice',
                        mastery_questions_answered={'novice': 0, 'competent': 0, 'proficient': 0, 'expert': 0, 'master': 0},
                        is_unlocked=True,
                        unlocked_at=datetime.now(timezone.utc)
                    )
                    session.add(skill_progress)
                    await session.commit()
                    print("✅ Unlocked root topic for user")
            return
        
        # Check if user exists
        user_result = await session.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            # Create default user
            print("👤 Creating default user...")
            user = User(
                id=1,
                email="user@example.com",
                username="testuser",
                hashed_password=pwd_context.hash("password123"),
                is_active=True
            )
            session.add(user)
        else:
            print("👤 Using existing user...")
        
        # Create root AI topic
        print("🌳 Creating root AI topic...")
        ai_topic = Topic(
            name="Artificial Intelligence",
            description="The study and development of computer systems able to perform tasks that typically require human intelligence",
            parent_id=None,
            difficulty_min=1,
            difficulty_max=10
        )
        session.add(ai_topic)
        await session.flush()  # Get the ID
        
        # Create initial skill progress for user
        print("📊 Creating initial skill progress...")
        skill_progress = UserSkillProgress(
            user_id=1,
            topic_id=ai_topic.id,
            questions_answered=0,
            correct_answers=0,
            mastery_level='novice',
            current_mastery_level='novice',
            mastery_questions_answered={'novice': 0, 'competent': 0, 'proficient': 0, 'expert': 0, 'master': 0},
            is_unlocked=True,
            unlocked_at=datetime.now(timezone.utc)
        )
        session.add(skill_progress)
        
        # Create unlock record
        print("🔓 Creating unlock record...")
        unlock = DynamicTopicUnlock(
            user_id=1,
            parent_topic_id=None,
            unlocked_topic_id=ai_topic.id,
            unlock_trigger="root_topic",
            unlocked_at=datetime.now(timezone.utc)
        )
        session.add(unlock)
        
        await session.commit()
        print("✅ Database initialized successfully!")
        print(f"   - User: user@example.com / password123")
        print(f"   - Root topic: {ai_topic.name}")

if __name__ == "__main__":
    asyncio.run(init_database())