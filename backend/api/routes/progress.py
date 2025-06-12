from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db

router = APIRouter()

@router.get("/")
async def get_progress(db: AsyncSession = Depends(get_db)):
    """Get user's learning progress"""
    # TODO: Implement progress tracking
    return {"progress": "Not implemented yet"}