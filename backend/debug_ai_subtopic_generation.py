"""
Debug script to test AI subtopic generation when reaching Competent level
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic, UserSkillProgress, DynamicTopicUnlock
from services.dynamic_ontology_service import dynamic_ontology_service

async def debug_ai_subtopic_generation():
    """Test subtopic generation for AI when user reaches Competent level"""
    
    async with AsyncSessionLocal() as session:
        print("🔍 DEBUG: AI Subtopic Generation")
        print("=" * 50)
        
        # 1. Check current AI topic status
        ai_result = await session.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = ai_result.scalar_one_or_none()
        
        if not ai_topic:
            print("❌ AI topic not found!")
            return
        
        print(f"✅ AI Topic found: ID={ai_topic.id}")
        
        # 2. Check current progress
        progress_result = await session.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.topic_id == ai_topic.id,
                UserSkillProgress.user_id == 1
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        if progress:
            print(f"📊 Current Progress:")
            print(f"   - Mastery Level: {progress.current_mastery_level}")
            print(f"   - Questions Answered: {progress.questions_answered}")
            print(f"   - Correct Answers: {progress.correct_answers}")
            print(f"   - Proficiency Threshold Met: {progress.proficiency_threshold_met}")
        else:
            print("❌ No progress found for AI topic!")
            return
        
        # 3. Check existing children
        children_result = await session.execute(
            select(Topic).where(Topic.parent_id == ai_topic.id)
        )
        existing_children = children_result.scalars().all()
        print(f"\n🌳 Current children count: {len(existing_children)}")
        for child in existing_children:
            print(f"   - {child.name} (ID={child.id})")
        
        # 4. If user is Competent but no children exist, manually trigger generation
        if progress.current_mastery_level == "competent" and len(existing_children) == 0:
            print(f"\n🎯 User is Competent but no children exist - triggering generation...")
            
            # Manually call the subtopic generation
            try:
                unlocked_topics = await dynamic_ontology_service.check_and_unlock_subtopics(
                    session, 1, ai_topic.id
                )
                
                print(f"✅ Generation completed! {len(unlocked_topics)} topics unlocked:")
                for topic in unlocked_topics:
                    print(f"   - {topic['name']}: {topic['unlock_reason']}")
                    
            except Exception as e:
                print(f"❌ Generation failed: {e}")
                import traceback
                traceback.print_exc()
        
        elif progress.current_mastery_level != "competent":
            print(f"\n⚠️ User is {progress.current_mastery_level}, not competent yet")
            print("   Need to reach Competent level to trigger subtopic generation")
        
        elif len(existing_children) > 0:
            print(f"\n✅ Children already exist - generation already happened")
        
        # 5. Final check - see if children were created
        final_children_result = await session.execute(
            select(Topic).where(Topic.parent_id == ai_topic.id)
        )
        final_children = final_children_result.scalars().all()
        
        print(f"\n📈 Final children count: {len(final_children)}")
        for child in final_children:
            print(f"   - {child.name} (ID={child.id})")

if __name__ == "__main__":
    asyncio.run(debug_ai_subtopic_generation())