from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    # Check if running on Vercel
    is_vercel = os.environ.get("VERCEL", "0") == "1"
    
    # Use PostgreSQL URL from environment or fallback to SQLite
    # On Vercel, SQLite must be in /tmp directory
    if is_vercel and not os.environ.get("POSTGRES_URL"):
        DATABASE_URL: str = "sqlite+aiosqlite:////tmp/relevia.db"
    else:
        DATABASE_URL: str = os.environ.get("POSTGRES_URL", "sqlite+aiosqlite:///./relevia.db")
    
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