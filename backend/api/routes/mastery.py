"""
API routes for mastery system
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List
from pydantic import BaseModel

from db.database import get_db
from services.mastery_progress_service import MasteryProgressService
from services.mastery_question_generator import MasteryQuestionGenerator
# from api.dependencies import get_current_user  # TODO: Add authentication
from core.mastery_levels import MasteryLevel, MASTERY_DESCRIPTIONS
from db.models import Topic
from sqlalchemy import select

router = APIRouter(prefix="/mastery", tags=["mastery"])

mastery_progress_service = MasteryProgressService()
mastery_generator = MasteryQuestionGenerator()

class StartMasterySessionRequest(BaseModel):
    topic_id: int
    mastery_level: str = "novice"

class MasteryAnswerRequest(BaseModel):
    mastery_level: str
    is_correct: bool

@router.get("/levels")
async def get_mastery_levels():
    """Get all available mastery levels and their descriptions"""
    return {
        "levels": MASTERY_DESCRIPTIONS,
        "progression": [level.value for level in [
            MasteryLevel.NOVICE,
            MasteryLevel.COMPETENT, 
            MasteryLevel.PROFICIENT,
            MasteryLevel.EXPERT,
            MasteryLevel.MASTER
        ]]
    }

@router.get("/user/{user_id}/overview")
async def get_user_mastery_overview(
    user_id: int,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Get overview of user's mastery across all topics"""
    # TODO: Add authorization check that user can access this data
    
    return await mastery_progress_service.get_mastery_overview(db, user_id)

@router.get("/user/{user_id}/topic/{topic_id}")
async def get_topic_mastery(
    user_id: int,
    topic_id: int,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Get user's mastery status for a specific topic"""
    # TODO: Add authorization check
    
    return await mastery_progress_service.get_user_mastery(db, user_id, topic_id)

@router.post("/user/{user_id}/topic/{topic_id}/record-answer")
async def record_mastery_answer(
    user_id: int,
    topic_id: int,
    request: MasteryAnswerRequest,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Record an answer for mastery progression"""
    # TODO: Add authorization check
    
    mastery_level = MasteryLevel(request.mastery_level)
    return await mastery_progress_service.record_mastery_answer(
        db, user_id, topic_id, mastery_level, request.is_correct
    )

@router.get("/user/{user_id}/topic/{topic_id}/recommended-level")
async def get_recommended_mastery_level(
    user_id: int,
    topic_id: int,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Get recommended mastery level for next question"""
    # TODO: Add authorization check
    
    recommended_level = await mastery_progress_service.get_recommended_mastery_level(
        db, user_id, topic_id
    )
    
    return {
        "recommended_level": recommended_level.value,
        "description": MASTERY_DESCRIPTIONS[recommended_level]
    }

@router.post("/generate-question")
async def generate_mastery_question(
    topic_id: int,
    mastery_level: str,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Generate a question for specific mastery level (for testing/admin)"""
    
    # Get topic
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    try:
        mastery_enum = MasteryLevel(mastery_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mastery level")
    
    question_data = await mastery_generator.generate_mastery_question(
        db, topic, mastery_enum
    )
    
    return question_data

@router.get("/topics-with-mastery")
async def get_topics_with_mastery_info(
    user_id: int,
    db: AsyncSession = Depends(get_db)
    # current_user = Depends(get_current_user)  # TODO: Add authentication
):
    """Get all topics with user's mastery information"""
    # TODO: Add authorization check
    
    # Get all topics user has progress on
    mastery_overview = await mastery_progress_service.get_mastery_overview(db, user_id)
    
    # Get basic topic info
    result = await db.execute(select(Topic).where(Topic.parent_id.isnot(None)))
    all_topics = result.scalars().all()
    
    # Combine topic info with mastery data
    topics_with_mastery = []
    mastery_by_topic = {tm["topic_id"]: tm for tm in mastery_overview["topics_mastery"]}
    
    for topic in all_topics:
        mastery_info = mastery_by_topic.get(topic.id, {
            "current_level": "novice",
            "progress": {"progress_percent": 0, "questions_needed": 8, "is_max_level": False},
            "can_navigate": False
        })
        
        topics_with_mastery.append({
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "parent_id": topic.parent_id,
            "mastery_level": mastery_info["current_level"],
            "mastery_progress": mastery_info["progress"],
            "can_navigate_tree": mastery_info.get("can_navigate", False)
        })
    
    return {
        "topics": topics_with_mastery,
        "mastery_summary": mastery_overview["level_distribution"]
    }