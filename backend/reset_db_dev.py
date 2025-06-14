#!/usr/bin/env python3
"""
Development Database Reset Script
Quick reset for development - drops and recreates all tables
WARNING: This will DELETE ALL DATA!
"""
import asyncio
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import create_async_engine
from db.database import engine, Base, AsyncSessionLocal
from db.models import Topic

async def reset_database():
    """Drop and recreate all tables"""
    print("🔄 Resetting database...")
    
    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        )
        tables = result.fetchall()
        
        # Disable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys = OFF;"))
        
        # Drop each table
        for table in tables:
            table_name = table[0]
            await conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
        
        # Re-enable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys = ON;"))
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize root topic
    async with AsyncSessionLocal() as db:
        ai_topic = Topic(
            name="Artificial Intelligence",
            description="The science and engineering of creating intelligent machines and computer programs",
            difficulty_min=1,
            difficulty_max=10
        )
        db.add(ai_topic)
        await db.commit()
        
        # Verify
        result = await db.execute(select(func.count(Topic.id)))
        count = result.scalar()
        print(f"✅ Database reset complete! Topics: {count}")

if __name__ == "__main__":
    asyncio.run(reset_database())