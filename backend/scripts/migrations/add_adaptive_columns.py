"""
Add adaptive learning columns to existing tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import engine


async def add_adaptive_columns():
    """Add columns needed for adaptive learning"""
    
    print("🔄 Adding adaptive learning columns...")
    print("=" * 50)
    
    async with AsyncSession(engine) as session:
        try:
            # Add session_type column to quiz_sessions
            print("📝 Adding session_type column to quiz_sessions...")
            await session.execute(text("""
                ALTER TABLE quiz_sessions 
                ADD COLUMN IF NOT EXISTS session_type VARCHAR DEFAULT 'topic_focused'
            """))
            
            # Make topic_id nullable for adaptive sessions
            print("📝 Making topic_id nullable in quiz_sessions...")
            await session.execute(text("""
                ALTER TABLE quiz_sessions 
                ALTER COLUMN topic_id DROP NOT NULL
            """))
            
            await session.commit()
            print("✅ Successfully added adaptive learning columns")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(add_adaptive_columns())