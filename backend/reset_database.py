#!/usr/bin/env python3
"""
Database Reset Script - Drops all tables and reinitializes the database
WARNING: This will DELETE ALL DATA in the database!
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from db.database import Base, engine
from core.config import settings
from db.models import *  # Import all models to ensure they're registered
from core.logging_config import logger


async def drop_all_tables():
    """Drop all tables in the database"""
    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = result.fetchall()
        
        if tables:
            print(f"Found {len(tables)} tables to drop:")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Drop all tables with CASCADE to handle foreign key constraints
            for table in tables:
                try:
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE'))
                    print(f"✓ Dropped table: {table[0]}")
                except Exception as e:
                    print(f"✗ Error dropping table {table[0]}: {e}")
        else:
            print("No tables found to drop.")
            
        await conn.commit()


async def create_all_tables():
    """Create all tables defined in the models"""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Created all tables")
        
        # Verify tables were created
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = result.fetchall()
        
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")


async def initialize_base_data():
    """Initialize base data including root AI topic"""
    from db.database import AsyncSessionLocal
    from db.models import Topic, User
    
    async with AsyncSessionLocal() as db:
        try:
            # Create demo user if needed
            user_result = await db.execute(
                text("SELECT id FROM users WHERE id = 1")
            )
            if not user_result.scalar():
                demo_user = User(
                    id=1,
                    email="demo@example.com",
                    username="demo",
                    hashed_password="demo"  # In production, this would be properly hashed
                )
                db.add(demo_user)
                print("✓ Created demo user")
            
            # Create root AI topic
            root_topic = Topic(
                name="Artificial Intelligence",
                description="The study of creating intelligent machines that can perform tasks requiring human intelligence",
                parent_id=None,
                difficulty_min=1,
                difficulty_max=10
            )
            db.add(root_topic)
            await db.flush()
            
            print(f"✓ Created root topic: {root_topic.name} (ID: {root_topic.id})")
            
            # Create user skill progress for root topic so it's unlocked
            from db.models import UserSkillProgress
            root_progress = UserSkillProgress(
                user_id=1,
                topic_id=root_topic.id,
                is_unlocked=True,
                skill_level=0.0,
                confidence=0.0,
                questions_answered=0,
                correct_answers=0,
                mastery_level="novice",
                current_mastery_level="novice",
                mastery_questions_answered={"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}
            )
            db.add(root_progress)
            print("✓ Unlocked root topic for demo user")
            
            await db.commit()
            print("\n✓ Database initialization complete!")
            
        except Exception as e:
            await db.rollback()
            print(f"\n✗ Error during initialization: {e}")
            raise


async def reset_database():
    """Main function to reset the database"""
    print("=" * 60)
    print("DATABASE RESET SCRIPT")
    print("=" * 60)
    print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print(f"Database: {settings.DATABASE_URL}")
    print("\nThis action cannot be undone.")
    
    # Confirm action
    response = input("\nAre you sure you want to continue? Type 'YES' to confirm: ")
    if response != "YES":
        print("\nDatabase reset cancelled.")
        return
    
    print("\nProceeding with database reset...\n")
    
    try:
        # Step 1: Drop all tables
        print("Step 1: Dropping all tables...")
        await drop_all_tables()
        
        # Step 2: Create all tables
        print("\nStep 2: Creating tables...")
        await create_all_tables()
        
        # Step 3: Initialize base data
        print("\nStep 3: Initializing base data...")
        await initialize_base_data()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Database reset failed: {e}")
        logger.error(f"Database reset failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Check if force flag is provided to skip confirmation
    force_mode = len(sys.argv) > 1 and sys.argv[1] == "--force"
    
    if force_mode:
        print("Force flag detected, skipping confirmation...")
        # Override input function
        import builtins
        original_input = builtins.input
        builtins.input = lambda x: "YES"
        
    try:
        asyncio.run(reset_database())
    finally:
        # Restore original input if we overrode it
        if force_mode:
            builtins.input = original_input