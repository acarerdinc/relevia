#!/usr/bin/env python3
"""
Database Migration: Add Question Diversity Tracking

Adds the TopicQuestionHistory table to track semantic question diversity
and prevent repetitive themes like "Transformer architecture obsession"
"""

import asyncio
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from core.config import settings
from core.logging_config import logger

async def run_migration():
    """Run the migration to add question diversity tracking"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    
    async with engine.begin() as conn:
        # Check if table already exists
        table_exists_result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'topic_question_history'
            );
        """))
        
        table_exists = table_exists_result.scalar()
        
        if table_exists:
            print("✅ TopicQuestionHistory table already exists, skipping migration")
            return
        
        print("🚀 Creating TopicQuestionHistory table...")
        
        # Create the new table
        await conn.execute(text("""
            CREATE TABLE topic_question_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                topic_id INTEGER NOT NULL REFERENCES topics(id),
                question_id INTEGER NOT NULL REFERENCES questions(id),
                session_id INTEGER NOT NULL REFERENCES quiz_sessions(id),
                question_content TEXT NOT NULL,
                extracted_concepts JSONB,
                asked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        
        # Create indexes for better performance
        await conn.execute(text("""
            CREATE INDEX idx_topic_question_history_user_topic 
            ON topic_question_history(user_id, topic_id);
        """))
        
        await conn.execute(text("""
            CREATE INDEX idx_topic_question_history_asked_at 
            ON topic_question_history(asked_at);
        """))
        
        await conn.execute(text("""
            CREATE INDEX idx_topic_question_history_session 
            ON topic_question_history(session_id);
        """))
        
        # Create GIN index for concept search
        await conn.execute(text("""
            CREATE INDEX idx_topic_question_history_concepts 
            ON topic_question_history USING GIN(extracted_concepts);
        """))
        
        print("✅ TopicQuestionHistory table and indexes created successfully!")
        print("🎯 Question diversity tracking is now active!")
        print()
        print("📊 This migration enables:")
        print("  - Semantic question diversity tracking")
        print("  - Prevention of repetitive themes (e.g., 'Transformer obsession')")
        print("  - Context-aware question generation")
        print("  - Concept cooldown periods")
        print("  - Historical question analysis")

async def main():
    """Main migration function"""
    try:
        await run_migration()
        print("\n🎉 Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())