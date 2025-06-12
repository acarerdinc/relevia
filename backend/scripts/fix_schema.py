#!/usr/bin/env python3
"""
Fix database schema for adaptive learning
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg


async def fix_schema():
    """Add missing columns to existing database"""
    
    print("🔧 Fixing database schema for adaptive learning...")
    print("=" * 50)
    
    # Connect directly to the database
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres", 
        password="password",
        database="relevia_db"
    )
    
    try:
        # Add session_type column if it doesn't exist
        print("📝 Adding session_type column to quiz_sessions...")
        await conn.execute("""
            ALTER TABLE quiz_sessions 
            ADD COLUMN IF NOT EXISTS session_type VARCHAR DEFAULT 'topic_focused'
        """)
        
        # Make topic_id nullable
        print("📝 Making topic_id nullable in quiz_sessions...")
        await conn.execute("""
            ALTER TABLE quiz_sessions 
            ALTER COLUMN topic_id DROP NOT NULL
        """)
        
        print("✅ Schema fixes applied successfully!")
        
    except Exception as e:
        print(f"❌ Schema fix failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_schema())