"""
Quick fix for timezone issues with SQLite
"""
from sqlalchemy import text
from db.database import engine
import asyncio

async def fix_datetime_columns():
    """
    SQLite doesn't handle timezone-aware datetimes well.
    This is a temporary fix for the MVP.
    """
    async with engine.begin() as conn:
        # Update any null datetime fields to current time
        tables_with_datetime = [
            ("users", "created_at"),
            ("quiz_sessions", "started_at"),
            ("user_skill_progress", "last_seen"),
            ("user_interests", "created_at"),
            ("dynamic_topic_unlocks", "unlocked_at"),
            ("learning_goals", "created_at"),
            ("topic_question_history", "asked_at")
        ]
        
        for table, column in tables_with_datetime:
            try:
                await conn.execute(
                    text(f"UPDATE {table} SET {column} = datetime('now') WHERE {column} IS NULL")
                )
            except Exception as e:
                print(f"Skipping {table}.{column}: {e}")
    
    print("✅ Fixed datetime columns")

if __name__ == "__main__":
    asyncio.run(fix_datetime_columns())