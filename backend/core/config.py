from pydantic_settings import BaseSettings
from typing import List, Optional
import os

# Check if running on Vercel
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Database URL configuration
# Check for Supabase/PostgreSQL on Vercel
postgres_url = os.environ.get("POSTGRES_URL")
database_url_env = os.environ.get("DATABASE_URL")

if is_vercel and (postgres_url or database_url_env):
    # Use PostgreSQL on Vercel
    default_database_url = postgres_url or database_url_env
    # Convert postgres:// to postgresql:// for SQLAlchemy
    if default_database_url.startswith("postgres://"):
        default_database_url = default_database_url.replace("postgres://", "postgresql://", 1)
    # Add asyncpg driver for async operations
    if "postgresql://" in default_database_url and "+asyncpg" not in default_database_url:
        default_database_url = default_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"[CONFIG] Using PostgreSQL database on Vercel")
else:
    # Local development - use SQLite
    default_database_url = "sqlite+aiosqlite:///./relevia.db"
    print(f"[CONFIG] Using SQLite database for local development")

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