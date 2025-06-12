from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db

router = APIRouter()

@router.post("/register")
async def register(db: AsyncSession = Depends(get_db)):
    # TODO: Implement user registration
    return {"message": "Registration endpoint"}

@router.post("/login")
async def login(db: AsyncSession = Depends(get_db)):
    # TODO: Implement user login
    return {"message": "Login endpoint"}