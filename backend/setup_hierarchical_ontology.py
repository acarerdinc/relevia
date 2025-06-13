#!/usr/bin/env python3
"""
Setup Hierarchical Ontology - Creates the comprehensive AI knowledge tree
Based on the user's excellent ontology example
"""

import asyncio
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from services.dynamic_ontology_builder import dynamic_ontology_builder
from db.models import Topic, UserSkillProgress, Question, QuizSession, QuizQuestion, UserInterest, DynamicTopicUnlock
from core.config import settings

async def setup_hierarchical_ontology():
    """Setup the comprehensive hierarchical ontology in the database"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False
    )
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("🌳 Setting up comprehensive hierarchical AI ontology...")
            
            # Clear existing data in proper order to handle foreign key constraints
            await db.execute(delete(QuizQuestion))
            await db.execute(delete(QuizSession))
            await db.execute(delete(DynamicTopicUnlock))
            await db.execute(delete(UserInterest))
            await db.execute(delete(UserSkillProgress))
            await db.execute(delete(Question))
            await db.execute(delete(Topic))
            await db.commit()
            print("✅ Cleared existing ontology data")
            
            # Create all topics from the master ontology in proper order
            created_topics = {}
            
            # Sort topics by level to ensure parents are created before children
            sorted_topics = sorted(
                dynamic_ontology_builder.MASTER_ONTOLOGY.items(),
                key=lambda x: x[1]['level']
            )
            
            for topic_key, topic_data in sorted_topics:
                # Find parent topic ID
                parent_id = None
                if topic_data['prerequisites']:
                    # Use the most direct parent (last prerequisite)
                    parent_key = topic_data['prerequisites'][-1]
                    if parent_key in created_topics:
                        parent_id = created_topics[parent_key]
                
                # Create the topic
                new_topic = Topic(
                    name=topic_data['name'],
                    description=topic_data['description'],
                    parent_id=parent_id,
                    difficulty_min=max(1, topic_data['level']),
                    difficulty_max=min(10, topic_data['level'] + 3)
                )
                
                db.add(new_topic)
                await db.flush()  # Get the ID
                
                created_topics[topic_key] = new_topic.id
                print(f"📚 Created topic: {topic_data['name']} (Level {topic_data['level']}, ID: {new_topic.id})")
            
            await db.commit()
            print(f"✅ Created {len(created_topics)} topics in hierarchical structure")
            
            # Create default user (ID=1) and unlock only the root AI topic
            user_id = 1
            ai_topic_id = created_topics.get('ai')
            
            if ai_topic_id:
                # Create user progress for the root AI topic only
                from datetime import datetime
                user_progress = UserSkillProgress(
                    user_id=user_id,
                    topic_id=ai_topic_id,
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
            
            print("\n🎯 Hierarchical ontology setup complete!")
            print("📊 Topic hierarchy structure:")
            print("   Level 0: AI (Root)")
            print("   Level 1: Major domains (ML, DL, NLP, CV, etc.)")
            print("   Level 2: Sub-domains (Supervised, Unsupervised, etc.)")
            print("   Level 3: Specific techniques (Regression, Classification, etc.)")
            print("   Level 4+: Algorithms and implementations")
            print("\n🚀 Users will now progress hierarchically from general to specific topics!")
            
        except Exception as e:
            print(f"❌ Error setting up hierarchical ontology: {str(e)}")
            await db.rollback()
            raise
        finally:
            await db.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(setup_hierarchical_ontology())