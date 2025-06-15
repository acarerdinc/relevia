#!/usr/bin/env python3
"""
Reset database by removing all questions and topics while preserving users
"""
import asyncio
import sys
sys.path.append('/Users/acar/projects/relevia/backend')

from db.database import AsyncSessionLocal
from sqlalchemy import text, delete
from db.models import (
    Question, QuizQuestion, Topic, UserSkillProgress, 
    DynamicTopicUnlock, UserInterest, QuizSession
)

async def reset_questions_and_topics():
    """Reset all questions and topics, preserve users"""
    async with AsyncSessionLocal() as db:
        try:
            print("🔄 Starting database reset (questions and topics only)...")
            
            # Delete in dependency order to avoid foreign key constraints
            
            # 1. Delete quiz questions first (references questions and quiz sessions)
            result = await db.execute(delete(QuizQuestion))
            print(f"✅ Deleted {result.rowcount} quiz questions")
            
            # 2. Delete quiz sessions 
            result = await db.execute(delete(QuizSession))
            print(f"✅ Deleted {result.rowcount} quiz sessions")
            
            # 3. Delete user skill progress (references topics)
            result = await db.execute(delete(UserSkillProgress))
            print(f"✅ Deleted {result.rowcount} user skill progress records")
            
            # 4. Delete dynamic topic unlocks (references topics)
            result = await db.execute(delete(DynamicTopicUnlock))
            print(f"✅ Deleted {result.rowcount} dynamic topic unlocks")
            
            # 5. Delete user interests (references topics)
            result = await db.execute(delete(UserInterest))
            print(f"✅ Deleted {result.rowcount} user interests")
            
            # 6. Delete all questions
            result = await db.execute(delete(Question))
            print(f"✅ Deleted {result.rowcount} questions")
            
            # 7. Delete all topics (delete children first, then parents)
            # Get all topics ordered by depth (children first)
            topics_result = await db.execute(
                text("""
                WITH RECURSIVE topic_depth AS (
                    -- Base case: topics with no children
                    SELECT id, name, parent_id, 0 as depth
                    FROM topics 
                    WHERE id NOT IN (SELECT DISTINCT parent_id FROM topics WHERE parent_id IS NOT NULL)
                    
                    UNION ALL
                    
                    -- Recursive case: topics that have children
                    SELECT t.id, t.name, t.parent_id, td.depth + 1
                    FROM topics t
                    JOIN topic_depth td ON t.id = td.parent_id
                )
                SELECT id, name FROM topic_depth ORDER BY depth ASC
                """)
            )
            
            topics_to_delete = topics_result.fetchall()
            print(f"📋 Found {len(topics_to_delete)} topics to delete")
            
            # Delete topics one by one to avoid constraint issues
            for topic_id, topic_name in topics_to_delete:
                await db.execute(text("DELETE FROM topics WHERE id = :id"), {"id": topic_id})
                print(f"  - Deleted topic: {topic_name} (ID: {topic_id})")
            
            # Reset auto-increment sequences (if table exists)
            try:
                await db.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('questions', 'topics', 'quiz_questions', 'quiz_sessions', 'user_skill_progress', 'dynamic_topic_unlocks', 'user_interests')"))
                print("✅ Reset auto-increment sequences")
            except Exception as seq_error:
                print(f"⚠️ Could not reset sequences (table may not exist): {seq_error}")
                # This is okay - sequences will auto-reset when new records are inserted
            
            await db.commit()
            print("🎉 Database reset completed successfully!")
            print("📊 Summary:")
            print("  - All questions deleted")
            print("  - All topics deleted") 
            print("  - All quiz sessions deleted")
            print("  - All user progress deleted")
            print("  - All topic unlocks deleted")
            print("  - All user interests deleted")
            print("  - Users preserved")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error during reset: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    asyncio.run(reset_questions_and_topics())