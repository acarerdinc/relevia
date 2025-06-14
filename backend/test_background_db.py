#!/usr/bin/env python3
"""
Test if background tasks can properly use database sessions
"""
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic
import traceback

async def test_background_db_operation():
    """Test database operations in a background task"""
    print("🔍 Testing background database operations...")
    
    async def background_task():
        try:
            print("📋 Background task started")
            async with AsyncSessionLocal() as db:
                print("✅ Created database session")
                
                # Try a simple query
                result = await db.execute(
                    select(Topic).where(Topic.name == "Artificial Intelligence")
                )
                ai_topic = result.scalar_one_or_none()
                print(f"✅ Query executed successfully. AI topic ID: {ai_topic.id if ai_topic else 'Not found'}")
                
                # Try to create a test topic
                test_topic = Topic(
                    name="Test Background Topic",
                    description="Testing background task DB operations",
                    parent_id=ai_topic.id if ai_topic else None,
                    difficulty_min=1,
                    difficulty_max=5
                )
                db.add(test_topic)
                print("✅ Added test topic to session")
                
                await db.flush()
                print(f"✅ Flushed session. Test topic ID: {test_topic.id}")
                
                await db.commit()
                print("✅ Committed transaction")
                
                # Verify it was created
                verify_result = await db.execute(
                    select(Topic).where(Topic.name == "Test Background Topic")
                )
                verified = verify_result.scalar_one_or_none()
                print(f"✅ Verification: Topic {'exists' if verified else 'NOT FOUND'}")
                
                # Clean up
                if verified:
                    await db.delete(verified)
                    await db.commit()
                    print("✅ Cleaned up test topic")
                    
        except Exception as e:
            print(f"❌ Background task failed: {e}")
            print(f"📚 Stack trace:\n{traceback.format_exc()}")
    
    # Test 1: Direct execution
    print("\n=== Test 1: Direct execution ===")
    await background_task()
    
    # Test 2: As asyncio task
    print("\n=== Test 2: As asyncio.create_task ===")
    task = asyncio.create_task(background_task())
    await task
    
    # Test 3: Fire and forget (like in the actual code)
    print("\n=== Test 3: Fire and forget ===")
    task = asyncio.create_task(background_task())
    # Give it time to complete
    await asyncio.sleep(2)
    
    print("\n✅ All tests completed")

if __name__ == "__main__":
    asyncio.run(test_background_db_operation())