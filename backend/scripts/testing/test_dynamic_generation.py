"""
Test dynamic topic generation by simulating user proficiency
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.database import engine
from db.models import UserSkillProgress, Topic
from services.dynamic_ontology_service import DynamicOntologyService

async def test_dynamic_generation():
    """Test dynamic topic generation by simulating proficiency"""
    print("🧪 Testing dynamic topic generation...")
    print("=" * 50)
    
    dynamic_service = DynamicOntologyService()
    
    async with AsyncSession(engine) as session:
        # Get the root AI topic
        result = await session.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = result.scalar_one_or_none()
        
        if not ai_topic:
            print("❌ Root AI topic not found!")
            return
        
        # Store the topic info early to avoid session issues
        topic_id = ai_topic.id
        topic_name = ai_topic.name
        
        print(f"📚 Found root topic: {topic_name} (ID: {topic_id})")
        
        # Simulate user answering questions and getting proficient
        user_id = 1
        
        # Update user progress to simulate proficiency
        await session.execute(
            update(UserSkillProgress)
            .where(UserSkillProgress.user_id == user_id)
            .where(UserSkillProgress.topic_id == topic_id)
            .values(
                questions_answered=10,
                correct_answers=8,  # 80% accuracy
                skill_level=0.8,
                confidence=0.8
            )
        )
        await session.commit()
        
        print(f"✅ Simulated user proficiency: 8/10 questions correct (80%)")
        
        # Trigger dynamic topic generation
        print(f"\n🚀 Triggering dynamic topic generation...")
        
        unlocked_topics = await dynamic_service.check_and_unlock_subtopics(
            session, user_id, topic_id
        )
        
        if unlocked_topics:
            print(f"\n🎉 Generated {len(unlocked_topics)} new topics:")
            for topic in unlocked_topics:
                print(f"  ✨ {topic['name']}")
                print(f"     {topic['description']}")
                print(f"     Reason: {topic['unlock_reason']}")
                print()
        else:
            print(f"\n🤔 No topics were generated. Let's check why...")
            
            # Check user progress
            progress_result = await session.execute(
                select(UserSkillProgress).where(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
            progress = progress_result.scalar_one_or_none()
            
            if progress:
                accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
                print(f"     Current accuracy: {accuracy:.2%}")
                print(f"     Questions answered: {progress.questions_answered}")
                print(f"     Proficiency threshold met: {progress.proficiency_threshold_met}")
                print(f"     Required minimum questions: {dynamic_service.min_questions_for_proficiency}")
                print(f"     Required accuracy: {dynamic_service.PROFICIENCY_THRESHOLDS['beginner']:.1%}")
        
        # Check what topics exist now
        print(f"\n📋 Current topics in database:")
        all_topics = await session.execute(select(Topic))
        for topic in all_topics.scalars().all():
            parent_name = ""
            if topic.parent_id:
                parent_result = await session.execute(select(Topic).where(Topic.id == topic.parent_id))
                parent = parent_result.scalar_one_or_none()
                parent_name = f" (child of {parent.name})" if parent else ""
            
            print(f"  • {topic.name}{parent_name}")

if __name__ == "__main__":
    asyncio.run(test_dynamic_generation())