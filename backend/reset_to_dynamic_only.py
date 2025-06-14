"""
Reset database to have only the root AI topic - everything else will be dynamically generated
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from db.database import AsyncSessionLocal
from db.models import Topic, UserSkillProgress, DynamicTopicUnlock, User, Question, QuizQuestion, QuizSession

async def reset_to_dynamic_only():
    """Reset database to have only root AI topic"""
    
    async with AsyncSessionLocal() as session:
        print("🔄 Clearing existing topics and progress...")
        
        # Use CASCADE to handle foreign key dependencies
        await session.execute(text("TRUNCATE TABLE topic_question_history CASCADE"))
        await session.execute(text("TRUNCATE TABLE quiz_questions CASCADE"))
        await session.execute(text("TRUNCATE TABLE quiz_sessions CASCADE"))
        await session.execute(text("TRUNCATE TABLE questions CASCADE"))
        await session.execute(text("TRUNCATE TABLE dynamic_topic_unlocks CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_skill_progress CASCADE"))
        await session.execute(text("TRUNCATE TABLE topic_prerequisites CASCADE"))
        await session.execute(text("TRUNCATE TABLE topics CASCADE"))
        
        print("✅ Cleared all existing topics")
        
        # Create only the root AI topic
        root_topic = Topic(
            name="Artificial Intelligence",
            description="The study and development of computer systems able to perform tasks that typically require human intelligence",
            parent_id=None,
            difficulty_min=1,
            difficulty_max=10
        )
        session.add(root_topic)
        await session.flush()
        
        print(f"✅ Created root topic: {root_topic.name} (ID: {root_topic.id})")
        
        # Create a default user if it doesn't exist
        user_result = await session.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            user = User(
                id=1,
                email="demo@example.com",
                username="demo",
                hashed_password="demo"
            )
            session.add(user)
            print("✅ Created default user")
        
        # Create initial progress for the root topic (unlocked)
        root_progress = UserSkillProgress(
            user_id=1,
            topic_id=root_topic.id,
            skill_level=0.5,
            confidence=0.5,
            questions_answered=0,
            correct_answers=0,
            mastery_level="novice",
            current_mastery_level="novice",
            is_unlocked=True,
            proficiency_threshold_met=False,
            mastery_questions_answered={"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}
        )
        session.add(root_progress)
        
        await session.commit()
        
        print("✅ Created initial progress for AI topic")
        print("\n🎯 System is now ready for fully dynamic topic generation!")
        print("   - When you reach Competent level in 'Artificial Intelligence',")
        print("     it will generate children like Machine Learning, Computer Vision, etc.")
        print("   - When you reach Competent in those, they'll generate their own children")
        print("   - Everything will be dynamically created based on your progress and interests")

if __name__ == "__main__":
    asyncio.run(reset_to_dynamic_only())