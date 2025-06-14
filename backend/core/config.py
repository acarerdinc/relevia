from pydantic_settings import BaseSettings
from typing import List, Optional
import os

# Check if running on Vercel
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Get database URL from environment
postgres_url = os.environ.get("POSTGRES_URL")

# Convert postgresql:// to postgresql+asyncpg:// for async support
if postgres_url and postgres_url.startswith("postgresql://"):
    postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Remove pgbouncer parameter if present (not compatible with asyncpg)
    if "?pgbouncer=true" in postgres_url:
        postgres_url = postgres_url.replace("?pgbouncer=true", "")

# Determine database URL based on environment
if is_vercel and not postgres_url:
    default_database_url = "sqlite+aiosqlite:////tmp/relevia.db"
else:
    default_database_url = "sqlite+aiosqlite:///./relevia.db"

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = postgres_url or default_database_url
    
    # Redis (optional, not used but may be in .env)
    REDIS_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
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