#!/usr/bin/env python3
"""
Comprehensive database initialization script for Relevia
Ensures the project works correctly when cloned and run locally
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, inspect
from db.database import engine, Base
from db.models import User, Topic, UserSkillProgress, DynamicTopicUnlock
from passlib.context import CryptContext
from core.logging_config import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def check_and_fix_schema(session: AsyncSession):
    """Check database schema and fix any missing columns"""
    print("🔍 Checking database schema...")
    
    # Get the inspector to check existing columns
    def sync_inspect(conn):
        inspector = inspect(conn)
        return {
            'tables': inspector.get_table_names(),
            'user_skill_progress_columns': inspector.get_columns('user_skill_progress') if 'user_skill_progress' in inspector.get_table_names() else []
        }
    
    # Run inspection in sync context
    async with engine.begin() as conn:
        info = await conn.run_sync(sync_inspect)
    
    # Check if user_skill_progress table exists and has required columns
    if 'user_skill_progress' in info['tables']:
        existing_columns = {col['name'] for col in info['user_skill_progress_columns']}
        required_columns = {
            'skill_level': 'REAL DEFAULT 0.5',
            'confidence': 'REAL DEFAULT 0.5'
        }
        
        # Add missing columns
        for col_name, col_def in required_columns.items():
            if col_name not in existing_columns:
                print(f"📝 Adding missing column: {col_name}")
                try:
                    await session.execute(text(f"ALTER TABLE user_skill_progress ADD COLUMN {col_name} {col_def}"))
                    await session.commit()
                except Exception as e:
                    if "duplicate column name" not in str(e).lower():
                        print(f"⚠️  Warning: Could not add column {col_name}: {e}")
                    await session.rollback()

async def create_default_user(session: AsyncSession) -> int:
    """Create default user if not exists"""
    # Check if user exists
    result = await session.execute(text("SELECT id FROM users WHERE id = 1"))
    if result.first():
        print("✅ Default user already exists")
        return 1
    
    print("👤 Creating default user...")
    user = User(
        id=1,
        email="user@example.com",
        username="testuser",
        hashed_password=pwd_context.hash("password123"),
        is_active=True
    )
    session.add(user)
    await session.flush()
    print("✅ Created user: user@example.com / password123")
    return user.id

async def create_root_topic(session: AsyncSession) -> int:
    """Create root AI topic if not exists"""
    # Check if any topics exist
    result = await session.execute(text("SELECT id FROM topics WHERE parent_id IS NULL LIMIT 1"))
    existing = result.first()
    if existing:
        print(f"✅ Root topic already exists (ID: {existing[0]})")
        return existing[0]
    
    print("🌳 Creating root AI topic...")
    topic = Topic(
        name="Artificial Intelligence",
        description="The study and development of computer systems able to perform tasks that typically require human intelligence",
        parent_id=None,
        difficulty_min=1,
        difficulty_max=10
    )
    session.add(topic)
    await session.flush()
    print(f"✅ Created root topic: {topic.name} (ID: {topic.id})")
    return topic.id

async def ensure_user_access(session: AsyncSession, user_id: int, topic_id: int):
    """Ensure user has access to root topic"""
    # Check if progress record exists
    result = await session.execute(
        text("SELECT id FROM user_skill_progress WHERE user_id = :user_id AND topic_id = :topic_id"),
        {"user_id": user_id, "topic_id": topic_id}
    )
    if result.first():
        print("✅ User already has access to root topic")
        return
    
    print("📊 Creating skill progress record...")
    progress = UserSkillProgress(
        user_id=user_id,
        topic_id=topic_id,
        skill_level=0.5,
        confidence=0.5,
        questions_answered=0,
        correct_answers=0,
        mastery_level='novice',
        current_mastery_level='novice',
        mastery_questions_answered={'novice': 0, 'competent': 0, 'proficient': 0, 'expert': 0, 'master': 0},
        is_unlocked=True,
        unlocked_at=datetime.now(timezone.utc),  # Use timezone-aware datetime
        proficiency_threshold_met=False
    )
    session.add(progress)
    
    # Create unlock record
    print("🔓 Creating unlock record...")
    unlock = DynamicTopicUnlock(
        user_id=user_id,
        parent_topic_id=None,
        unlocked_topic_id=topic_id,
        unlock_trigger="root_topic",
        unlocked_at=datetime.now(timezone.utc)  # Use timezone-aware datetime
    )
    session.add(unlock)
    print("✅ Granted user access to root topic")

async def fix_datetime_issues(session: AsyncSession):
    """Fix any timezone issues in the database"""
    print("🕐 Fixing datetime timezone issues...")
    
    # Update any NULL or timezone-naive datetime fields
    tables_to_fix = [
        ('quiz_sessions', 'started_at'),
        ('user_skill_progress', 'unlocked_at'),
        ('dynamic_topic_unlocks', 'unlocked_at')
    ]
    
    for table, column in tables_to_fix:
        try:
            # Update NULL values to current time
            await session.execute(
                text(f"UPDATE {table} SET {column} = :now WHERE {column} IS NULL"),
                {"now": datetime.now(timezone.utc).isoformat()}
            )
            await session.commit()
        except Exception as e:
            print(f"⚠️  Could not fix {table}.{column}: {e}")
            await session.rollback()

async def verify_setup(session: AsyncSession):
    """Verify the database is properly set up"""
    print("\n📋 Verifying database setup...")
    
    checks = []
    
    # Check users
    result = await session.execute(text("SELECT COUNT(*) FROM users"))
    user_count = result.scalar()
    checks.append(f"Users: {user_count}")
    
    # Check topics
    result = await session.execute(text("SELECT COUNT(*) FROM topics"))
    topic_count = result.scalar()
    checks.append(f"Topics: {topic_count}")
    
    # Check user progress
    result = await session.execute(text("SELECT COUNT(*) FROM user_skill_progress"))
    progress_count = result.scalar()
    checks.append(f"User progress records: {progress_count}")
    
    # Check unlocks
    result = await session.execute(text("SELECT COUNT(*) FROM dynamic_topic_unlocks"))
    unlock_count = result.scalar()
    checks.append(f"Topic unlocks: {unlock_count}")
    
    print("✅ Database status:")
    for check in checks:
        print(f"   - {check}")

async def init_database():
    """Main initialization function"""
    print("🚀 Relevia Database Initialization")
    print("=" * 50)
    
    try:
        # Create all tables
        print("📊 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")
        
        async with AsyncSession(engine) as session:
            # Fix schema issues
            await check_and_fix_schema(session)
            
            # Create default data
            user_id = await create_default_user(session)
            topic_id = await create_root_topic(session)
            await ensure_user_access(session, user_id, topic_id)
            
            # Fix datetime issues
            await fix_datetime_issues(session)
            
            # Commit all changes
            await session.commit()
            
            # Verify setup
            await verify_setup(session)
        
        print("\n✅ Database initialization complete!")
        print("   You can now run the application and log in with:")
        print("   Email: user@example.com")
        print("   Password: password123")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        logger.error(f"Database initialization error: {e}", exc_info=True)
        raise

async def main():
    """Run initialization"""
    await init_database()

if __name__ == "__main__":
    # Check if we're in the backend directory
    if not os.path.exists("main.py"):
        print("❌ Please run this script from the backend directory")
        sys.exit(1)
    
    asyncio.run(main())