#!/usr/bin/env python3
"""
Complete Database Reset Script
Drops ALL tables and recreates the entire database schema from scratch
WARNING: This will DELETE ALL DATA permanently!
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from db.database import engine, Base, AsyncSessionLocal
from db.models import (
    User, Topic, UserSkillProgress, UserInterest, 
    DynamicTopicUnlock, LearningGoal, QuizSession, 
    QuizQuestion, Question, Choice, TeachingRecord,
    CurriculumProgress
)

async def drop_all_tables():
    """Drop all tables in the database"""
    print("🗑️  Dropping all tables...")
    
    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        )
        tables = result.fetchall()
        
        # Disable foreign key constraints temporarily
        await conn.execute(text("PRAGMA foreign_keys = OFF;"))
        
        # Drop each table
        for table in tables:
            table_name = table[0]
            print(f"   Dropping table: {table_name}")
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
        
        # Re-enable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys = ON;"))
    
    print("✅ All tables dropped successfully")

async def create_all_tables():
    """Create all tables from models"""
    print("\n🏗️  Creating all tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ All tables created successfully")

async def initialize_root_topic():
    """Create the root AI topic"""
    print("\n🌱 Initializing root topic...")
    
    async with AsyncSessionLocal() as db:
        # Check if AI topic already exists (shouldn't after reset)
        result = await db.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence", Topic.parent_id == None)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            # Create root AI topic
            ai_topic = Topic(
                name="Artificial Intelligence",
                description="The science and engineering of creating intelligent machines and computer programs",
                difficulty_min=1,
                difficulty_max=10
            )
            db.add(ai_topic)
            await db.commit()
            print(f"✅ Created root topic: {ai_topic.name} (ID: {ai_topic.id})")
        else:
            print("ℹ️  Root AI topic already exists")

async def verify_database():
    """Verify the database is properly reset"""
    print("\n🔍 Verifying database state...")
    
    async with AsyncSessionLocal() as db:
        # Count all major tables
        tables_to_check = [
            ("Topics", Topic),
            ("Users", User),
            ("Questions", Question),
            ("Quiz Sessions", QuizSession),
            ("User Progress", UserSkillProgress),
            ("User Interests", UserInterest),
            ("Dynamic Unlocks", DynamicTopicUnlock),
            ("Teaching Records", TeachingRecord)
        ]
        
        for table_name, model in tables_to_check:
            result = await db.execute(select(func.count(model.id)))
            count = result.scalar()
            print(f"   {table_name}: {count} records")

async def main():
    """Main reset function"""
    print("=" * 60)
    print("COMPLETE DATABASE RESET")
    print("WARNING: This will DELETE ALL DATA permanently!")
    print("=" * 60)
    
    # Confirm with user
    confirm = input("\nAre you ABSOLUTELY SURE you want to reset the entire database? (type 'YES' to confirm): ")
    if confirm != "YES":
        print("❌ Reset cancelled")
        return
    
    # Double confirmation for safety
    confirm2 = input("This is your LAST CHANCE. All data will be PERMANENTLY DELETED. Continue? (type 'DELETE ALL' to confirm): ")
    if confirm2 != "DELETE ALL":
        print("❌ Reset cancelled")
        return
    
    try:
        # Drop all tables
        await drop_all_tables()
        
        # Create all tables
        await create_all_tables()
        
        # Initialize root topic
        await initialize_root_topic()
        
        # Verify
        await verify_database()
        
        print("\n✅ Database reset completed successfully!")
        print("ℹ️  The database is now empty except for the root AI topic")
        
    except Exception as e:
        print(f"\n❌ Error during reset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Add import for select and func
    from sqlalchemy import select, func
    
    asyncio.run(main())