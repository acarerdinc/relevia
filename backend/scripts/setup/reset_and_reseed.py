"""
Reset database and seed with truly minimal infinite ontology - just AI root topic
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.database import engine, Base
from db.models import (
    Topic, TopicPrerequisite, UserSkillProgress, 
    UserInterest, DynamicTopicUnlock, LearningGoal,
    QuizSession, QuizQuestion, Question
)
from data.enhanced_ai_ontology import ENHANCED_AI_ONTOLOGY, ENHANCED_PREREQUISITES

async def reset_database():
    """Clean all progress and dynamic data, keep topics structure"""
    print("🧹 Cleaning database...")
    
    async with AsyncSession(engine) as session:
        # Delete in proper order to respect foreign key constraints
        await session.execute(delete(QuizQuestion))
        await session.execute(delete(QuizSession))
        await session.execute(delete(UserSkillProgress))
        await session.execute(delete(UserInterest))
        await session.execute(delete(DynamicTopicUnlock))
        await session.execute(delete(LearningGoal))
        await session.execute(delete(Question))  # Delete questions before topics
        await session.execute(delete(TopicPrerequisite))
        await session.execute(delete(Topic))
        
        await session.commit()
        print("✅ Database cleaned")

async def create_minimal_ontology(session: AsyncSession) -> dict:
    """Create only the AI root topic for infinite dynamic expansion"""
    topic_map = {}
    
    # Create ONLY the AI root topic
    ai_root = Topic(
        name="Artificial Intelligence",
        description="The study and development of computer systems able to perform tasks that typically require human intelligence",
        parent_id=None,
        difficulty_min=1,
        difficulty_max=10
    )
    session.add(ai_root)
    await session.flush()  # Get the ID
    
    topic_map["Artificial Intelligence"] = ai_root.id
    print(f"✅ Created AI root topic: {ai_root.name} (ID: {ai_root.id})")
    print(f"🌱 All other topics will be generated dynamically based on user exploration")
    
    return topic_map

async def create_prerequisites(session: AsyncSession, topic_map: dict):
    """No prerequisites needed for minimal ontology"""
    print("\n🔗 No prerequisites needed - minimal ontology")
    # Skip prerequisites for minimal setup

async def initialize_root_only(session: AsyncSession, topic_map: dict, user_id: int = 1):
    """Initialize progress with ONLY the root AI topic unlocked"""
    print(f"\n👤 Initializing minimal progress for user {user_id}...")
    
    # Only unlock the root "Artificial Intelligence" topic
    root_topic_name = "Artificial Intelligence"
    
    if root_topic_name in topic_map:
        topic_id = topic_map[root_topic_name]
        
        progress = UserSkillProgress(
            user_id=user_id,
            topic_id=topic_id,
            skill_level=0.0,  # Start at 0
            confidence=0.0,   # Start at 0
            mastery_level="novice",
            is_unlocked=True,
            unlocked_at=datetime.utcnow()
        )
        session.add(progress)
        print(f"   • Unlocked: {root_topic_name} (only root topic)")
    
    print(f"🎯 Starting with minimal ontology - just the root topic!")

async def reset_and_reseed():
    """Main function to reset and reseed database"""
    print("🔄 Resetting database and reseeding with minimal ontology...")
    print("=" * 60)
    
    # Reset database
    await reset_database()
    
    # Recreate tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        print("\n🌱 Creating minimal infinite ontology...")
        # Create ONLY the AI root topic - everything else is generated dynamically
        topic_map = await create_minimal_ontology(session)
        
        # No prerequisites needed for minimal setup
        await create_prerequisites(session, topic_map)
        
        # Only unlock root topic for default user
        await initialize_root_only(session, topic_map)
        
        # Commit everything
        await session.commit()
        
        print(f"\n🎉 Minimal infinite ontology ready!")
        print(f"✅ Total topics created: {len(topic_map)} (AI root only)")
        print(f"✅ All other topics will be generated dynamically")
        print(f"✅ True infinite ontology tree implementation")
        print(f"\n🚀 Ready for adaptive exploration/exploitation learning!")

if __name__ == "__main__":
    asyncio.run(reset_and_reseed())