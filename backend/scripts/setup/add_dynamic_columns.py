"""
Add missing columns for dynamic ontology features
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import engine

async def add_missing_columns():
    """Add missing columns to existing tables"""
    print("🔄 Adding missing columns for dynamic ontology features...")
    
    async with engine.begin() as conn:
        # Add columns to user_skill_progress table
        try:
            await conn.execute(text("""
                ALTER TABLE user_skill_progress 
                ADD COLUMN IF NOT EXISTS mastery_level VARCHAR DEFAULT 'novice',
                ADD COLUMN IF NOT EXISTS is_unlocked BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS unlocked_at TIMESTAMP,
                ADD COLUMN IF NOT EXISTS proficiency_threshold_met BOOLEAN DEFAULT FALSE
            """))
            print("✅ Added columns to user_skill_progress table")
        except Exception as e:
            print(f"ℹ️  user_skill_progress columns may already exist: {e}")
        
        # Add columns to quiz_questions table
        try:
            await conn.execute(text("""
                ALTER TABLE quiz_questions 
                ADD COLUMN IF NOT EXISTS user_action VARCHAR DEFAULT 'answer',
                ADD COLUMN IF NOT EXISTS interest_signal FLOAT DEFAULT 0.0
            """))
            print("✅ Added columns to quiz_questions table")
        except Exception as e:
            print(f"ℹ️  quiz_questions columns may already exist: {e}")
    
    print("✅ Column migration completed!")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())