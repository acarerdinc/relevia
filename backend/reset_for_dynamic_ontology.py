#!/usr/bin/env python3
"""
Reset database for dynamic ontology system - removes all predefined topics
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from services.dynamic_ontology_builder import dynamic_ontology_builder
from db.models import Topic, UserSkillProgress, Question, QuizSession, QuizQuestion, UserInterest, DynamicTopicUnlock
from core.config import settings
from datetime import datetime

async def reset_for_dynamic_ontology():
    """Reset database and start with only root AI topic for dynamic generation"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("🗑️  Clearing all existing data for fresh dynamic ontology start...")
            
            # Clear existing data in proper order to handle foreign key constraints
            await db.execute(delete(QuizQuestion))
            await db.execute(delete(QuizSession))
            await db.execute(delete(DynamicTopicUnlock))
            await db.execute(delete(UserInterest))
            await db.execute(delete(UserSkillProgress))
            await db.execute(delete(Question))
            await db.execute(delete(Topic))
            await db.commit()
            print("✅ Cleared all existing data")
            
            # Create only the root AI topic
            root_topic = Topic(
                name=dynamic_ontology_builder.root_topic["name"],
                description=dynamic_ontology_builder.root_topic["description"],
                parent_id=None,
                difficulty_min=1,
                difficulty_max=4
            )
            
            db.add(root_topic)
            await db.flush()  # Get the ID
            root_topic_id = root_topic.id
            
            print(f"📚 Created root topic: {dynamic_ontology_builder.root_topic['name']} (ID: {root_topic_id})")
            
            # Create default user (ID=1) and unlock only the root AI topic
            user_id = 1
            user_progress = UserSkillProgress(
                user_id=user_id,
                topic_id=root_topic_id,
                skill_level=0.0,
                confidence=0.0,
                questions_answered=0,
                correct_answers=0,
                mastery_level="novice",
                is_unlocked=True,
                unlocked_at=datetime.utcnow()
            )
            
            db.add(user_progress)
            await db.commit()
            print(f"✅ Unlocked root AI topic for user {user_id}")
            
            print("\n🎯 Dynamic ontology system ready!")
            print("🌳 The system will now generate child topics dynamically as users progress")
            print("📈 Topics will unlock hierarchically based on mastery")
            print("♾️  Infinite ontology tree is now enabled!")
            
        except Exception as e:
            print(f"❌ Error resetting for dynamic ontology: {str(e)}")
            await db.rollback()
            raise
        finally:
            await db.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_for_dynamic_ontology())