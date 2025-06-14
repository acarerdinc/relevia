"""
Database initialization for Vercel serverless environment
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select
from db.models import User, Topic, UserSkillProgress, Base
from api.routes.auth import get_password_hash
from datetime import datetime
from core.logging_config import logger

# Global flag to track initialization
_initialized = False

async def ensure_database_initialized():
    """Ensure database is initialized for serverless environment"""
    global _initialized
    
    # Skip if already initialized in this instance
    if _initialized:
        return
    
    try:
        # Get database URL from environment
        database_url = os.environ.get("POSTGRES_URL")
        if not database_url:
            # Fallback to SQLite in /tmp for Vercel
            if os.environ.get("VERCEL") == "1":
                database_url = "sqlite+aiosqlite:////tmp/relevia.db"
            else:
                database_url = "sqlite+aiosqlite:///./relevia.db"
        
        # Create engine for this initialization
        engine = create_async_engine(database_url, echo=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Check if data exists
        async with AsyncSession(engine) as db:
            result = await db.execute(select(User).limit(1))
            if result.scalar_one_or_none():
                logger.info("Database already has data")
                _initialized = True
                await engine.dispose()
                return
            
            logger.info("Initializing database with users and topics...")
            
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
            
            created_users = []
            for user_data in users:
                hashed_password = get_password_hash(user_data["password"])
                new_user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=hashed_password,
                    is_active=True
                )
                db.add(new_user)
                created_users.append(new_user)
            
            await db.commit()
            
            # Refresh users to get IDs
            for user in created_users:
                await db.refresh(user)
            
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
            
            # Create initial skill progress for first user
            skill_progress = UserSkillProgress(
                user_id=created_users[0].id,
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
            
            logger.info("Database initialized successfully!")
            _initialized = True
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise