#!/usr/bin/env python3
"""
Debug script to manually trigger subtopic generation for testing
"""
import asyncio
import sys
sys.path.append('.')

from db.database import AsyncSessionLocal
from services.dynamic_ontology_service import dynamic_ontology_service

async def manual_trigger_subtopics(user_id: int = 1, topic_id: int = 1):
    """Manually trigger subtopic generation for debugging"""
    print(f"🔧 [DEBUG] Manually triggering subtopic generation...")
    print(f"🎯 [DEBUG] Target: user_id={user_id}, topic_id={topic_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Force trigger subtopic generation
            unlocked_topics = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, user_id, topic_id
            )
            
            print(f"✅ [DEBUG] Manual trigger completed!")
            print(f"📊 [DEBUG] Result: {len(unlocked_topics)} topics unlocked")
            
            if unlocked_topics:
                print(f"🎆 [DEBUG] Unlocked topics:")
                for topic in unlocked_topics:
                    print(f"  - {topic['name']}: {topic['description']}")
            else:
                print(f"❌ [DEBUG] No topics were unlocked")
                
        except Exception as e:
            print(f"💥 [DEBUG] Manual trigger failed: {e}")
            import traceback
            traceback.print_exc()

async def reset_proficiency_flag(user_id: int = 1, topic_id: int = 1):
    """Reset the proficiency_threshold_met flag to allow re-triggering"""
    print(f"🔄 [DEBUG] Resetting proficiency_threshold_met flag...")
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import text
        try:
            await db.execute(
                text("UPDATE user_skill_progress SET proficiency_threshold_met = 0 WHERE user_id = :user_id AND topic_id = :topic_id"),
                {"user_id": user_id, "topic_id": topic_id}
            )
            await db.commit()
            print(f"✅ [DEBUG] Flag reset successfully!")
        except Exception as e:
            print(f"💥 [DEBUG] Flag reset failed: {e}")

if __name__ == "__main__":
    print("🔧 Debug Subtopic Generation")
    print("1. Manual trigger")
    print("2. Reset proficiency flag + manual trigger")
    
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(manual_trigger_subtopics())
    elif choice == "2":
        asyncio.run(reset_proficiency_flag())
        asyncio.run(manual_trigger_subtopics())
    else:
        print("Invalid choice")