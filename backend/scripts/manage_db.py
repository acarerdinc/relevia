#!/usr/bin/env python3
"""
Database management script for Relevia
Handles migrations and initialization for both development and production
"""
import asyncio
import os
import sys
from pathlib import Path
import subprocess

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.supabase_config import get_async_engine, get_sync_engine
from db.models import Base
from passlib.context import CryptContext
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Test users configuration
TEST_USERS = [
    {
        "email": "info@acarerdinc.com",
        "username": "acarerdinc",
        "password": "fenapass1",
        "is_active": True
    },
    {
        "email": "ogulcancelik@gmail.com", 
        "username": "ogulcancelik",
        "password": "ordekzeze1",
        "is_active": True
    },
    {
        "email": "begumcitamak@gmail.com",
        "username": "begumcitamak", 
        "password": "zazapass1",
        "is_active": True
    }
]

async def create_tables():
    """Create all tables from models"""
    engine = get_async_engine()
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()

async def insert_test_users():
    """Insert test users if they don't exist"""
    engine = get_async_engine()
    
    try:
        async with engine.connect() as conn:
            # Check if users exist
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            
            if count > 0:
                print(f"ℹ Database already has {count} users")
                return
            
            print("Creating test users...")
            
            # Insert users
            for user_data in TEST_USERS:
                hashed_password = pwd_context.hash(user_data["password"])
                
                await conn.execute(
                    text("""
                        INSERT INTO users (email, username, hashed_password, is_active)
                        VALUES (:email, :username, :hashed_password, :is_active)
                        ON CONFLICT (email) DO NOTHING
                    """),
                    {
                        "email": user_data["email"],
                        "username": user_data["username"],
                        "hashed_password": hashed_password,
                        "is_active": user_data["is_active"]
                    }
                )
                print(f"✓ Created user: {user_data['email']}")
            
            await conn.commit()
            print("\n✓ All test users created successfully!")
            
    except Exception as e:
        print(f"❌ Error inserting users: {e}")
        raise
    finally:
        await engine.dispose()

def run_alembic_migrations():
    """Run Alembic migrations"""
    print("Running database migrations...")
    
    backend_dir = Path(__file__).parent.parent
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Migrations completed successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Migration failed:")
        print(result.stderr)
        raise Exception("Migration failed")

def create_alembic_migration(message: str):
    """Create a new Alembic migration"""
    print(f"Creating migration: {message}")
    
    backend_dir = Path(__file__).parent.parent
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Migration created successfully")
        print(result.stdout)
    else:
        print("❌ Failed to create migration:")
        print(result.stderr)
        raise Exception("Failed to create migration")

async def initialize_database(use_migrations=True):
    """Initialize database with tables and test data"""
    print("Initializing Relevia database...")
    print(f"Database type: {settings.DATABASE_URL.split(':')[0]}")
    
    if use_migrations:
        # Use Alembic for schema management
        run_alembic_migrations()
    else:
        # Direct table creation
        await create_tables()
    
    # Insert test users
    await insert_test_users()
    
    print("\n✅ Database initialization complete!")

async def reset_database():
    """Drop and recreate all tables (DANGEROUS!)"""
    print("⚠️  WARNING: This will DELETE all data!")
    response = input("Are you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    engine = get_async_engine()
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("✓ All tables dropped")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ All tables recreated")
    finally:
        await engine.dispose()
    
    # Insert test users
    await insert_test_users()
    
    print("\n✅ Database reset complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Relevia database")
    parser.add_argument("command", choices=["init", "migrate", "create-migration", "reset", "add-users"],
                       help="Command to run")
    parser.add_argument("--message", "-m", help="Migration message (for create-migration)")
    parser.add_argument("--no-migrations", action="store_true", 
                       help="Skip Alembic migrations and create tables directly")
    
    args = parser.parse_args()
    
    if args.command == "init":
        asyncio.run(initialize_database(use_migrations=not args.no_migrations))
    elif args.command == "migrate":
        run_alembic_migrations()
    elif args.command == "create-migration":
        if not args.message:
            print("Error: --message is required for create-migration")
            sys.exit(1)
        create_alembic_migration(args.message)
    elif args.command == "reset":
        asyncio.run(reset_database())
    elif args.command == "add-users":
        asyncio.run(insert_test_users())