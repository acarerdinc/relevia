#!/usr/bin/env python3
"""
Test AI subtopic generation directly
"""
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic, UserSkillProgress
from services.dynamic_ontology_service import dynamic_ontology_service

async def test_ai_subtopic_generation():
    """Test generating subtopics for AI topic"""
    
    async with AsyncSessionLocal() as db:
        # Get AI topic
        ai_result = await db.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = ai_result.scalar_one()
        print(f"✅ Found AI topic: ID={ai_topic.id}")
        
        # Check current children
        children_result = await db.execute(
            select(Topic).where(Topic.parent_id == ai_topic.id)
        )
        current_children = children_result.scalars().all()
        print(f"📊 Current children: {len(current_children)}")
        
        # Get or create user progress
        progress_result = await db.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.user_id == 1,
                UserSkillProgress.topic_id == ai_topic.id
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        if progress:
            print(f"📈 User progress: mastery={progress.current_mastery_level}, questions={progress.questions_answered}")
        else:
            print("❌ No user progress found!")
            return
            
        # Force set to competent if needed
        if progress.current_mastery_level != "competent":
            print(f"⚙️ Setting mastery to competent (was {progress.current_mastery_level})")
            progress.current_mastery_level = "competent"
            progress.questions_answered = 8  # Ensure enough questions
            await db.commit()
        
        print("\n🎯 Testing subtopic generation...")
        print("="*60)
        
        # Call the service directly
        try:
            result = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, 1, ai_topic.id
            )
            print(f"\n✅ Generation completed! Result: {len(result)} topics")
            
            if result:
                print("\n📋 Generated topics:")
                for topic in result:
                    print(f"  - {topic['name']}")
            else:
                print("\n❌ No topics were generated/unlocked")
                
            # Check final state
            final_children_result = await db.execute(
                select(Topic).where(Topic.parent_id == ai_topic.id)
            )
            final_children = final_children_result.scalars().all()
            print(f"\n📊 Final children count: {len(final_children)}")
            
            if final_children:
                print("\n📋 All children:")
                for child in final_children:
                    print(f"  - {child.name} (ID: {child.id})")
                    
        except Exception as e:
            print(f"\n❌ Generation failed: {e}")
            import traceback
            print(f"📚 Stack trace:\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_ai_subtopic_generation())