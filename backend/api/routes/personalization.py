from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from services.dynamic_ontology_service import dynamic_ontology_service

router = APIRouter()

@router.get("/ontology/{user_id}")
async def get_personalized_ontology(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get the personalized topic tree for a user"""
    try:
        ontology = await dynamic_ontology_service.get_user_personalized_ontology(db, user_id)
        return ontology
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/{user_id}")
async def get_topic_recommendations(user_id: int, limit: int = 5, db: AsyncSession = Depends(get_db)):
    """Get personalized topic recommendations"""
    try:
        recommendations = await dynamic_ontology_service.get_personalized_topic_recommendations(
            db, user_id, limit
        )
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interests/{user_id}")
async def get_user_interests(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user's interest profile"""
    from sqlalchemy import select
    from db.models import UserInterest, Topic
    
    try:
        result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, UserInterest.topic_id == Topic.id)
            .where(UserInterest.user_id == user_id)
            .order_by(UserInterest.interest_score.desc())
        )
        
        interests = []
        for interest, topic in result.all():
            interests.append({
                "topic": {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description
                },
                "interest_score": interest.interest_score,
                "interaction_count": interest.interaction_count,
                "time_spent": interest.time_spent,
                "preference_type": interest.preference_type
            })
        
        return {"interests": interests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{user_id}")
async def get_user_progress(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user's learning progress with mastery levels"""
    from sqlalchemy import select
    from db.models import UserSkillProgress, Topic
    
    try:
        result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(UserSkillProgress.user_id == user_id)
            .order_by(UserSkillProgress.skill_level.desc())
        )
        
        progress = []
        for skill_progress, topic in result.all():
            progress.append({
                "topic": {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description,
                    "difficulty_min": topic.difficulty_min,
                    "difficulty_max": topic.difficulty_max
                },
                "skill_level": skill_progress.skill_level,
                "confidence": skill_progress.confidence,
                "mastery_level": skill_progress.mastery_level,
                "questions_answered": skill_progress.questions_answered,
                "correct_answers": skill_progress.correct_answers,
                "accuracy": skill_progress.correct_answers / skill_progress.questions_answered if skill_progress.questions_answered > 0 else 0,
                "is_unlocked": skill_progress.is_unlocked,
                "unlocked_at": skill_progress.unlocked_at,
                "proficiency_threshold_met": skill_progress.proficiency_threshold_met
            })
        
        return {"progress": progress}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unlocks/{user_id}")
async def get_recent_unlocks(user_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get recent topic unlocks for user"""
    from sqlalchemy import select
    from db.models import DynamicTopicUnlock, Topic
    
    try:
        result = await db.execute(
            select(DynamicTopicUnlock, Topic)
            .join(Topic, DynamicTopicUnlock.unlocked_topic_id == Topic.id)
            .where(DynamicTopicUnlock.user_id == user_id)
            .order_by(DynamicTopicUnlock.unlocked_at.desc())
            .limit(limit)
        )
        
        unlocks = []
        for unlock, topic in result.all():
            unlocks.append({
                "topic": {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description
                },
                "unlock_trigger": unlock.unlock_trigger,
                "unlocked_at": unlock.unlocked_at
            })
        
        return {"recent_unlocks": unlocks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))