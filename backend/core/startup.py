"""
Startup tasks for Relevia backend
Ensures database is properly initialized on every startup
"""
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine, Base
from core.logging_config import logger
from datetime import datetime, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def ensure_database_initialized():
    """Ensure database is properly initialized on startup"""
    try:
        # Create tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with AsyncSession(engine) as session:
            # Quick check if database is initialized
            result = await session.execute(text("SELECT COUNT(*) FROM topics"))
            topic_count = result.scalar()
            
            if topic_count == 0:
                logger.info("Empty database detected, running initialization...")
                
                # Create default user
                result = await session.execute(text("SELECT COUNT(*) FROM users WHERE id = 1"))
                if result.scalar() == 0:
                    await session.execute(
                        text("""
                            INSERT INTO users (id, email, username, hashed_password, is_active)
                            VALUES (1, 'user@example.com', 'testuser', :password, 1)
                        """),
                        {"password": pwd_context.hash("password123")}
                    )
                
                # Create root topic
                await session.execute(
                    text("""
                        INSERT INTO topics (name, description, parent_id, difficulty_min, difficulty_max)
                        VALUES ('Artificial Intelligence', 
                                'The study and development of computer systems able to perform tasks that typically require human intelligence',
                                NULL, 1, 10)
                    """)
                )
                
                # Get the topic ID
                result = await session.execute(text("SELECT id FROM topics WHERE parent_id IS NULL LIMIT 1"))
                topic_id = result.scalar()
                
                # Create user progress with proper columns
                await session.execute(
                    text("""
                        INSERT INTO user_skill_progress 
                        (user_id, topic_id, questions_answered, correct_answers, 
                         mastery_level, current_mastery_level, mastery_questions_answered,
                         is_unlocked, unlocked_at, proficiency_threshold_met)
                        VALUES (1, :topic_id, 0, 0, 'novice', 'novice', 
                                :mastery_data,
                                1, :now, 0)
                    """),
                    {
                        "topic_id": topic_id,
                        "mastery_data": '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
                        "now": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                # Try to add skill_level and confidence if they exist in the model
                try:
                    await session.execute(
                        text("UPDATE user_skill_progress SET skill_level = 0.5, confidence = 0.5 WHERE user_id = 1")
                    )
                except:
                    pass  # Columns might not exist in this schema version
                
                # Create unlock record
                await session.execute(
                    text("""
                        INSERT INTO dynamic_topic_unlocks 
                        (user_id, parent_topic_id, unlocked_topic_id, unlock_trigger, unlocked_at)
                        VALUES (1, NULL, :topic_id, 'root_topic', :now)
                    """),
                    {
                        "topic_id": topic_id,
                        "now": datetime.now(timezone.utc).isoformat()
                    }
                )
                
                await session.commit()
                logger.info("✅ Database initialized with default data")
            else:
                logger.info(f"✅ Database already initialized ({topic_count} topics found)")
                
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
        # Don't raise - let the app start anyway