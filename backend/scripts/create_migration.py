#!/usr/bin/env python3
"""
Create an Alembic migration from current models
"""
import subprocess
import sys
from pathlib import Path

# Change to backend directory
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

def create_migration():
    """Create a new migration based on model changes"""
    print("Creating migration from current models...")
    
    # Run alembic command
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", "Initial schema"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Migration created successfully!")
        print(result.stdout)
    else:
        print("❌ Error creating migration:")
        print(result.stderr)
        return False
    
    return True

def run_migration():
    """Apply migrations to database"""
    print("\nApplying migrations...")
    
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Migrations applied successfully!")
        print(result.stdout)
    else:
        print("❌ Error applying migrations:")
        print(result.stderr)
        return False
    
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage database migrations")
    parser.add_argument("--create", action="store_true", help="Create a new migration")
    parser.add_argument("--run", action="store_true", help="Run pending migrations")
    parser.add_argument("--both", action="store_true", help="Create and run migrations")
    
    args = parser.parse_args()
    
    if args.both or args.create:
        create_migration()
    
    if args.both or args.run:
        run_migration()
    
    if not any([args.create, args.run, args.both]):
        print("Usage: python create_migration.py [--create] [--run] [--both]")