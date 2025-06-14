from pydantic_settings import BaseSettings
from typing import List, Optional
import os

# Check if running on Vercel
is_vercel = os.environ.get("VERCEL", "0") == "1"

# Database URL configuration
turso_url = os.environ.get("TURSO_DATABASE_URL")
turso_token = os.environ.get("TURSO_AUTH_TOKEN")

if turso_url and turso_token:
    # Use Turso database with authentication
    default_database_url = f"{turso_url}?authToken={turso_token}"
    print(f"[CONFIG] Using Turso database: {turso_url[:50]}...")
else:
    # Fallback to SQLite for local development
    if is_vercel:
        default_database_url = "sqlite+aiosqlite:////tmp/relevia.db"
    else:
        default_database_url = "sqlite+aiosqlite:///./relevia.db"
    print(f"[CONFIG] Using SQLite database: {default_database_url}")

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