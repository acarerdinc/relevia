"""Auth routes with Turso-compatible queries"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr

from db.database import get_db, is_turso
from db.models import User
from core.config import settings
from core.logging_config import logger

# Import original auth functions
from .auth import (
    pwd_context, oauth2_scheme, UserRegister, UserLogin, Token, UserResponse,
    verify_password, get_password_hash, create_access_token, get_current_user
)

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_turso(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login endpoint optimized for Turso"""
    logger.info(f"Login attempt for: {form_data.username}")
    
    try:
        if is_turso:
            # Use raw SQL for Turso
            query = text("""
                SELECT id, email, username, hashed_password, is_active, created_at 
                FROM users 
                WHERE email = :email
            """)
            result = await db.execute(query, {"email": form_data.username})
            row = result.fetchone()
            
            if row:
                user = type('User', (), {
                    'id': row[0],
                    'email': row[1],
                    'username': row[2],
                    'hashed_password': row[3],
                    'is_active': row[4],
                    'created_at': row[5]
                })()
            else:
                user = None
        else:
            # Use ORM for regular databases
            from sqlalchemy import select
            result = await db.execute(select(User).where(User.email == form_data.username))
            user = result.scalar_one_or_none()
            
    except Exception as e:
        logger.error(f"Database error during login for {form_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    logger.info(f"Successful login for: {user.email}")
    
    return Token(access_token=access_token, token_type="bearer")