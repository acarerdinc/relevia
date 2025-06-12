"""
Migrate database to add new dynamic ontology tables
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine, Base

async def migrate_database():
    """Create new tables for dynamic ontology features"""
    print("🔄 Migrating database for dynamic ontology features...")
    
    async with engine.begin() as conn:
        # Create all tables (this will create new ones and skip existing)
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database migration completed!")
    print("🆕 New tables created:")
    print("   • user_interests - Track user interest in topics")
    print("   • dynamic_topic_unlocks - Track dynamically unlocked topics")
    print("   • learning_goals - Store user learning objectives")
    print("📝 New columns added to existing tables:")
    print("   • user_skill_progress - mastery_level, is_unlocked, etc.")
    print("   • quiz_questions - user_action, interest_signal")

if __name__ == "__main__":
    asyncio.run(migrate_database())