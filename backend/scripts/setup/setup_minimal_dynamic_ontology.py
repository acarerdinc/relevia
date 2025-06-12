"""
Setup minimal dynamic ontology - just the AI root topic
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.database import engine, Base
from db.models import (
    Topic, TopicPrerequisite, UserSkillProgress, 
    UserInterest, DynamicTopicUnlock, LearningGoal,
    QuizSession, QuizQuestion, Question
)

async def setup_minimal_ontology():
    """Set up minimal dynamic ontology with just AI root topic"""
    print("🔄 Setting up minimal dynamic ontology...")
    print("=" * 60)
    
    async with AsyncSession(engine) as session:
        # Clean all existing data
        print("🧹 Cleaning existing data...")
        await session.execute(delete(QuizQuestion))
        await session.execute(delete(QuizSession))
        await session.execute(delete(UserSkillProgress))
        await session.execute(delete(UserInterest))
        await session.execute(delete(DynamicTopicUnlock))
        await session.execute(delete(LearningGoal))
        await session.execute(delete(Question))
        await session.execute(delete(TopicPrerequisite))
        await session.execute(delete(Topic))
        
        await session.commit()
        print("✅ Database cleaned")
        
        # Create just the root AI topic
        print("\n🌱 Creating root AI topic...")
        ai_topic = Topic(
            name="Artificial Intelligence",
            description="The study and development of computer systems able to perform tasks that typically require human intelligence",
            parent_id=None,
            difficulty_min=1,
            difficulty_max=10
        )
        session.add(ai_topic)
        await session.flush()  # Get the ID
        
        print(f"✅ Created root topic: {ai_topic.name} (ID: {ai_topic.id})")
        
        # Initialize progress for default user (ID: 1)
        user_id = 1
        initial_progress = UserSkillProgress(
            user_id=user_id,
            topic_id=ai_topic.id,
            skill_level=0.0,
            confidence=0.0,
            mastery_level="novice",
            is_unlocked=True,
            unlocked_at=datetime.utcnow()
        )
        session.add(initial_progress)
        
        print(f"✅ Unlocked root topic for user {user_id}")
        
        await session.commit()
        
        print(f"\n🎉 Minimal dynamic ontology setup completed!")
        print(f"✅ Starting with single root topic: 'Artificial Intelligence'")
        print(f"✅ Subtopics will be generated dynamically as users demonstrate proficiency")
        print(f"🚀 Ready for infinite ontology expansion!")

if __name__ == "__main__":
    asyncio.run(setup_minimal_ontology())