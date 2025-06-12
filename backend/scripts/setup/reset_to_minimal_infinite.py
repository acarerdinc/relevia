"""
Reset database to truly minimal infinite ontology - only AI root topic
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import engine
from db.models import Topic, UserSkillProgress, User


async def reset_to_minimal_infinite():
    """Reset to minimal infinite ontology with only AI root"""
    
    print("🌱 Resetting to Minimal Infinite Ontology...")
    print("=" * 50)
    
    async with AsyncSession(engine) as session:
        try:
            # Clean all existing data
            print("🧹 Cleaning existing topics and progress...")
            
            # Delete in correct order to avoid foreign key issues
            await session.execute("DELETE FROM quiz_questions")
            await session.execute("DELETE FROM quiz_sessions") 
            await session.execute("DELETE FROM user_skill_progress")
            await session.execute("DELETE FROM user_interests")
            await session.execute("DELETE FROM dynamic_topic_unlocks")
            await session.execute("DELETE FROM learning_goals")
            await session.execute("DELETE FROM questions")
            await session.execute("DELETE FROM topic_prerequisites")
            await session.execute("DELETE FROM topics")
            
            print("✅ All topics deleted")
            
            # Create ONLY the AI root topic
            print("🌳 Creating minimal infinite ontology...")
            
            ai_root = Topic(
                name="Artificial Intelligence",
                description="The study and development of computer systems able to perform tasks that typically require human intelligence",
                parent_id=None,
                difficulty_min=1,
                difficulty_max=10
            )
            
            session.add(ai_root)
            await session.flush()
            
            print(f"✅ Created AI root topic: {ai_root.name} (ID: {ai_root.id})")
            
            # Create user progress record for AI root (unlocked by default)
            # Check if user 1 exists
            user_result = await session.get(User, 1)
            if user_result:
                ai_progress = UserSkillProgress(
                    user_id=1,
                    topic_id=ai_root.id,
                    skill_level=0.5,
                    confidence=0.5,
                    questions_answered=0,
                    correct_answers=0,
                    is_unlocked=True,
                    mastery_level="novice"
                )
                
                session.add(ai_progress)
                print(f"✅ Unlocked AI root for user 1")
            else:
                print("⚠️  User 1 not found - skipping progress creation")
            
            await session.commit()
            
            print("\n🎯 Infinite Ontology Ready!")
            print("📊 Starting state:")
            print(f"   - Total topics: 1 (AI root only)")
            print(f"   - All other topics will be generated dynamically")
            print(f"   - Infinite expansion based on user exploration")
            
        except Exception as e:
            print(f"❌ Reset failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(reset_to_minimal_infinite())