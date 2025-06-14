"""
Raw SQL authentication to bypass all ORM and prepared statement issues
"""
from fastapi import APIRouter, HTTPException, status, Form
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import asyncpg
from core.config import settings
from core.logging_config import logger

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.post("/login-raw", response_model=Token)
async def login_raw(username: str = Form(...), password: str = Form(...)):
    """Raw SQL login that completely bypasses SQLAlchemy"""
    logger.info(f"Raw login attempt for: {username}")
    
    try:
        # Get the raw PostgreSQL URL
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Connect with minimal settings - no statement caching
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        
        try:
            # Use a simple parameterized query
            query = """
                SELECT id, username, email, hashed_password 
                FROM users 
                WHERE email = $1
            """
            
            # Execute without prepare
            row = await conn.fetchrow(query, username)
            
            if not row:
                logger.warning(f"User not found: {username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            # Verify password
            if not pwd_context.verify(password, row['hashed_password']):
                logger.warning(f"Invalid password for: {username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            # Create access token
            access_token = create_access_token(data={"sub": row['email']})
            logger.info(f"Successful raw login for: {row['email']}")
            
            return Token(access_token=access_token, token_type="bearer")
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )