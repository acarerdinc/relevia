from pydantic_settings import BaseSettings
from typing import List, Optional
import os

# Check if running on Vercel
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Database URL configuration
# Check for Supabase/PostgreSQL on Vercel
postgres_url = os.environ.get("POSTGRES_URL")
database_url_env = os.environ.get("DATABASE_URL")

# ALWAYS use PostgreSQL on Vercel, fail if not configured
if is_vercel:
    if not (postgres_url or database_url_env):
        raise ValueError("POSTGRES_URL or DATABASE_URL must be set on Vercel")
    
    # Use PostgreSQL on Vercel
    default_database_url = postgres_url or database_url_env
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if default_database_url.startswith("postgres://"):
        default_database_url = default_database_url.replace("postgres://", "postgresql://", 1)
    # Add asyncpg driver for async operations
    if "postgresql://" in default_database_url and "+asyncpg" not in default_database_url:
        default_database_url = default_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"[CONFIG] Using PostgreSQL database on Vercel: {default_database_url[:30]}...")
else:
    # Local development - check for DATABASE_URL in env
    local_db_url = os.environ.get("DATABASE_URL")
    if local_db_url:
        # Use provided DATABASE_URL (PostgreSQL or SQLite)
        default_database_url = local_db_url
        # Add asyncpg driver if PostgreSQL
        if "postgresql://" in default_database_url and "+asyncpg" not in default_database_url:
            default_database_url = default_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        print(f"[CONFIG] Using DATABASE_URL from environment: {default_database_url[:30]}...")
    else:
        # No database configured
        raise ValueError(
            "DATABASE_URL must be set for local development. "
            "Options:\n"
            "1. Use Supabase: Set DATABASE_URL to your Supabase connection string\n"
            "2. Use local PostgreSQL: Set DATABASE_URL=postgresql://user:pass@localhost:5432/dbname\n"
            "3. Copy .env.example to .env and configure"
        )

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = default_database_url
    
    # Redis (optional, not used but may be in .env)
    REDIS_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "development-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Gemini AI
    GEMINI_API_KEY: str = ""
    
    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "relevia-skills"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001", 
        "https://relevia.vercel.app",
        "https://relevia-frontend.vercel.app",
        "https://relevia-backend.vercel.app"
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()