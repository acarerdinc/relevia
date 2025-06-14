#!/usr/bin/env python3
"""
Debug script to trace subtopic generation trigger issues
"""
import asyncio
import sys
sys.path.append('/Users/acar/projects/relevia/backend')

from sqlalchemy import select, and_
from db.database import AsyncSessionLocal
from db.models import UserSkillProgress, Topic, DynamicTopicUnlock
from services.dynamic_ontology_service import dynamic_ontology_service

async def debug_subtopic_generation():
    """Debug why subtopics aren't generated on first Competent achievement"""
    
    async with AsyncSessionLocal() as db:
        # Get a user with competent mastery level
        result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(UserSkillProgress.current_mastery_level == "competent")
            .order_by(UserSkillProgress.id.desc())
            .limit(5)
        )
        
        for progress, topic in result:
            print(f"\n{'='*60}")
            print(f"User {progress.user_id} - Topic: {topic.name} (ID: {topic.id})")
            print(f"Mastery Level: {progress.current_mastery_level}")
            print(f"Questions Answered: {progress.questions_answered}")
            print(f"Proficiency Threshold Met: {progress.proficiency_threshold_met}")
            
            # Check if topic has children
            children_result = await db.execute(
                select(Topic).where(Topic.parent_id == topic.id)
            )
            children = children_result.scalars().all()
            print(f"Has Children: {len(children) > 0} (Count: {len(children)})")
            
            # Check unlocks
            unlocks_result = await db.execute(
                select(DynamicTopicUnlock)
                .where(
                    and_(
                        DynamicTopicUnlock.user_id == progress.user_id,
                        DynamicTopicUnlock.parent_topic_id == topic.id
                    )
                )
            )
            unlocks = unlocks_result.scalars().all()
            print(f"Existing Unlocks: {len(unlocks)}")
            
            # Check generation condition
            current_mastery_level = progress.current_mastery_level or "novice"
            has_children = len(children) > 0
            
            should_generate_subtopics = (
                # First time reaching competent level (no children exist yet)
                (current_mastery_level in ["competent", "proficient", "expert", "master"] and not has_children) or
                # Progressive generation for higher mastery levels
                (current_mastery_level in ["proficient", "expert", "master"] and has_children)
            )
            
            print(f"\nGeneration Logic:")
            print(f"  - Current mastery in required levels: {current_mastery_level in ['competent', 'proficient', 'expert', 'master']}")
            print(f"  - Has no children (for first time): {not has_children}")
            print(f"  - Should generate: {should_generate_subtopics}")
            
            # Also check min questions requirement
            min_questions = dynamic_ontology_service.min_questions_for_proficiency
            print(f"  - Min questions required: {min_questions}")
            print(f"  - Meets min questions: {progress.questions_answered >= min_questions}")
            
            # Try to trigger generation manually
            if should_generate_subtopics and progress.questions_answered >= min_questions:
                print(f"\n🔧 Manually triggering subtopic generation...")
                try:
                    result = await dynamic_ontology_service.check_and_unlock_subtopics(
                        db, progress.user_id, topic.id
                    )
                    print(f"✅ Generation result: {len(result)} topics generated/unlocked")
                    for unlocked in result:
                        print(f"   - {unlocked['name']}: {unlocked['unlock_reason']}")
                except Exception as e:
                    print(f"❌ Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_subtopic_generation())