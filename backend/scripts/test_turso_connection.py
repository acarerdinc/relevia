"""Test Turso database connection locally"""
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import Settings

async def test_connection():
    settings = Settings()
    print(f"DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    
    try:
        # Create engine
        engine = create_async_engine(settings.DATABASE_URL)
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connection successful!")
            
            # Check if users table exists
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"✓ Users table exists with {count} users")
            
            # List users
            result = await conn.execute(text("SELECT email FROM users"))
            users = result.fetchall()
            print("\nExisting users:")
            for user in users:
                print(f"  - {user[0]}")
                
        await engine.dispose()
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_connection())