#!/usr/bin/env python3
"""
Fix database schema using SQLAlchemy
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from db.database import engine


async def fix_schema():
    """Add missing columns to existing database"""
    
    print("🔧 Fixing database schema for adaptive learning...")
    print("=" * 50)
    
    async with AsyncSession(engine) as session:
        try:
            # Add session_type column if it doesn't exist
            print("📝 Adding session_type column to quiz_sessions...")
            await session.execute(text("""
                ALTER TABLE quiz_sessions 
                ADD COLUMN IF NOT EXISTS session_type VARCHAR DEFAULT 'topic_focused'
            """))
            
            # Make topic_id nullable
            print("📝 Making topic_id nullable in quiz_sessions...")
            await session.execute(text("""
                ALTER TABLE quiz_sessions 
                ALTER COLUMN topic_id DROP NOT NULL
            """))
            
            await session.commit()
            print("✅ Schema fixes applied successfully!")
            
        except Exception as e:
            print(f"❌ Schema fix failed: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(fix_schema())