"""
Test major domains by directly simulating proficiency achievement
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.database import engine
from db.models import UserSkillProgress, Topic
from services.dynamic_ontology_service import DynamicOntologyService

async def test_direct_unlock():
    """Test by directly setting high proficiency and triggering unlock"""
    print("🔧 Testing Direct Proficiency Simulation")
    print("=" * 50)
    
    dynamic_service = DynamicOntologyService()
    
    async with AsyncSession(engine) as session:
        try:
            # Find the AI root topic
            result = await session.execute(
                select(Topic).where(Topic.name == "Artificial Intelligence")
            )
            ai_topic = result.scalar_one_or_none()
            
            if not ai_topic:
                print("❌ AI root topic not found!")
                return
                
            print(f"🧠 Found AI topic: {ai_topic.name} (ID: {ai_topic.id})")
            
            # Update user progress to simulate high proficiency
            await session.execute(
                update(UserSkillProgress)
                .where(UserSkillProgress.user_id == 1)
                .where(UserSkillProgress.topic_id == ai_topic.id)
                .values(
                    questions_answered=8,
                    correct_answers=6,  # 75% accuracy
                    skill_level=0.75,
                    confidence=0.7,
                    proficiency_threshold_met=False  # Not yet triggered
                )
            )
            await session.commit()
            
            print(f"📊 Simulated proficiency: 6/8 questions (75% accuracy)")
            
            # Check current thresholds
            print(f"🎯 Proficiency thresholds:")
            for level, threshold in dynamic_service.PROFICIENCY_THRESHOLDS.items():
                print(f"   {level}: {threshold:.1%}")
            
            print(f"🔢 Minimum questions required: {dynamic_service.min_questions_for_proficiency}")
            
            # Trigger the unlock check
            print(f"\n🚀 Triggering dynamic topic generation...")
            
            unlocked_topics = await dynamic_service.check_and_unlock_subtopics(
                session, user_id=1, topic_id=ai_topic.id
            )
            
            if unlocked_topics:
                print(f"\n🎉 SUCCESS! Generated {len(unlocked_topics)} major AI domains:")
                for topic in unlocked_topics:
                    print(f"   ✨ {topic['name']}")
                    print(f"      {topic['description']}")
                    print(f"      Reason: {topic['unlock_reason']}")
                    print()
            else:
                print(f"\n🤔 No topics unlocked. Checking why...")
                
                # Debug the progress state
                progress_result = await session.execute(
                    select(UserSkillProgress).where(
                        UserSkillProgress.user_id == 1,
                        UserSkillProgress.topic_id == ai_topic.id
                    )
                )
                progress = progress_result.scalar_one_or_none()
                
                if progress:
                    accuracy = progress.correct_answers / progress.questions_answered
                    print(f"   📊 Current state:")
                    print(f"      Questions: {progress.questions_answered}")
                    print(f"      Accuracy: {accuracy:.1%}")
                    print(f"      Threshold met: {progress.proficiency_threshold_met}")
                    print(f"      Skill level: {progress.skill_level}")
                    print(f"      Mastery: {progress.mastery_level}")
                    
                    # Check children count
                    children_result = await session.execute(
                        select(Topic).where(Topic.parent_id == ai_topic.id)
                    )
                    existing_children = children_result.scalars().all()
                    print(f"      Existing children: {len(existing_children)}")
                    
                    if accuracy >= dynamic_service.PROFICIENCY_THRESHOLDS["beginner"]:
                        print(f"   ✅ Accuracy meets threshold")
                    else:
                        print(f"   ❌ Accuracy below threshold")
                        
                    if progress.questions_answered >= dynamic_service.min_questions_for_proficiency:
                        print(f"   ✅ Enough questions answered")
                    else:
                        print(f"   ❌ Need more questions")
            
            # Show final topic state
            print(f"\n📋 Final Topic State:")
            all_topics_result = await session.execute(select(Topic))
            all_topics = all_topics_result.scalars().all()
            
            for topic in all_topics:
                parent_info = ""
                if topic.parent_id:
                    parent_result = await session.execute(select(Topic).where(Topic.id == topic.parent_id))
                    parent = parent_result.scalar_one_or_none()
                    parent_info = f" (child of {parent.name})" if parent else ""
                
                print(f"   📚 {topic.name}{parent_info}")
                
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_unlock())