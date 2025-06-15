#!/usr/bin/env python3
"""Test script to manually trigger subtopic generation for a user who reached competent level"""

import asyncio
import sys
sys.path.append('/Users/acar/projects/relevia/backend')

from db.database import AsyncSessionLocal
from services.dynamic_ontology_service import dynamic_ontology_service

async def test_subtopic_generation():
    """Test subtopic generation for user 1 on topic 1"""
    async with AsyncSessionLocal() as db:
        try:
            print("🧪 Testing subtopic generation...")
            print("User ID: 1, Topic ID: 1 (Artificial Intelligence)")
            
            # Trigger subtopic generation
            result = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, user_id=1, topic_id=1
            )
            
            if result:
                print(f"✅ Successfully unlocked {len(result)} subtopics:")
                for topic in result:
                    print(f"  - {topic['name']}: {topic['description']}")
            else:
                print("❌ No subtopics were generated/unlocked")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subtopic_generation())