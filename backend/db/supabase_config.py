"""Supabase database configuration for Vercel deployment"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

def get_supabase_url():
    """Get the correct Supabase URL for the connection type"""
    # These should be set in Vercel environment variables
    postgres_url = os.environ.get("POSTGRES_URL")  # For direct connections
    postgres_prisma_url = os.environ.get("POSTGRES_PRISMA_URL")  # For Prisma
    postgres_url_non_pooling = os.environ.get("POSTGRES_URL_NON_POOLING")  # For migrations
    
    # For serverless functions, use the pooled connection
    if postgres_url:
        return postgres_url
    
    # Fallback to DATABASE_URL if set
    return os.environ.get("DATABASE_URL", "")

def get_async_engine():
    """Create async engine with proper configuration for Supabase"""
    database_url = get_supabase_url()
    
    if not database_url:
        raise ValueError("No database URL configured. Set POSTGRES_URL in environment variables.")
    
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # For async, we need to use asyncpg driver
    if "postgresql://" in database_url and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Create engine with NullPool for serverless
    # This is recommended for PgBouncer transaction pooling
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,  # Verify connections before using
        poolclass=NullPool,  # Don't pool connections (PgBouncer handles this)
        echo=False
    )
    
    return engine

def get_sync_engine():
    """Create sync engine for migrations and initialization"""
    database_url = os.environ.get("POSTGRES_URL_NON_POOLING") or get_supabase_url()
    
    if not database_url:
        raise ValueError("No database URL configured")
    
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Use psycopg2 for sync operations
    if "postgresql://" in database_url and "+psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )
    
    return engine