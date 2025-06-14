from pydantic_settings import BaseSettings
from typing import List, Optional
import os

# Check if running on Vercel
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Get database URL from environment
postgres_url = os.environ.get("POSTGRES_URL")
print(f"[CONFIG] Raw POSTGRES_URL: {postgres_url[:50] if postgres_url else 'None'}...")

# Convert postgresql:// to postgresql+asyncpg:// for async support
if postgres_url:
    # Check if it's postgres:// (transaction pooler) vs postgresql:// (direct)
    if postgres_url.startswith("postgres://"):
        postgres_url = postgres_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # For Supabase connections, ensure proper SSL handling
    if "supabase.co" in postgres_url or "pooler.supabase.com" in postgres_url:
        # asyncpg requires different SSL parameter format
        # Remove any existing ssl/sslmode parameters
        import re
        postgres_url = re.sub(r'[?&](ssl|sslmode|pgbouncer)=[^&]*', '', postgres_url)
        # Add asyncpg-compatible SSL parameter
        if "?" in postgres_url:
            postgres_url += "&ssl=require"
        else:
            postgres_url += "?ssl=require"
        
        # For transaction pooler, we'll need to handle prepared statements differently
        # Don't add server_settings to URL - it needs to be passed to create_async_engine

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