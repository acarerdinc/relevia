from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from db.database import get_db
from services.dynamic_ontology_builder import dynamic_ontology_builder
from core.logging_config import logger
from typing import Optional

router = APIRouter()

class LearningRequest(BaseModel):
    request_text: str
    user_id: int = 1

class TopicNavigationRequest(BaseModel):
    topic_id: int
    user_id: int = 1

class InterestUpdateRequest(BaseModel):
    topic_id: int
    user_id: int = 1
    action: str = "start_learning"

@router.post("/request-learning")
async def request_learning_topic(
    request: LearningRequest, 
    db: AsyncSession = Depends(get_db)
):
    """
    Process user's free text learning request and create/unlock appropriate topic
    """
    
    if not request.request_text or len(request.request_text.strip()) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Please provide a meaningful learning request (at least 3 characters)"
        )
    
    if len(request.request_text.strip()) > 500:
        raise HTTPException(
            status_code=400,
            detail="Learning request too long. Please keep it under 500 characters"
        )
    
    try:
        logger.info(f"Processing learning request from user {request.user_id}: '{request.request_text}'")
        
        # Use dynamic ontology builder to process the request
        result = await dynamic_ontology_builder.create_user_requested_topic(
            db=db,
            user_id=request.user_id,
            learning_request=request.request_text
        )
        
        return {
            "success": result["success"],
            "action": result["action"],
            "topic_id": result["topic_id"],
            "topic_name": result["topic_name"],
            "message": result["message"],
            "confidence": result.get("confidence", 1.0),
            "reasoning": result.get("reasoning", ""),
            "parent_name": result.get("parent_name")
        }
        
    except Exception as e:
        logger.error(f"Error processing learning request: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to process your learning request. Please try again."
        )

@router.post("/navigate-to-topic")
async def navigate_to_topic(
    request: TopicNavigationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Navigate user to a specific topic and ensure it's unlocked for them
    """
    
    try:
        # Unlock the topic for the user and set interest
        await dynamic_ontology_builder._unlock_topic_for_user(db, request.user_id, request.topic_id)
        await dynamic_ontology_builder._set_user_interest(db, request.user_id, request.topic_id, 0.8, "navigation")
        await db.commit()
        
        return {
            "success": True,
            "topic_id": request.topic_id,
            "message": "Successfully navigated to topic"
        }
        
    except Exception as e:
        logger.error(f"Error navigating to topic {request.topic_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to navigate to the requested topic"
        )

@router.get("/suggestions")
async def get_learning_suggestions(
    user_id: int = 1,
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Get learning suggestions based on user's current progress and interests
    """
    
    try:
        # Get next recommended topics from the ontology builder
        recommendations = await dynamic_ontology_builder.get_learning_path_recommendation(
            db=db,
            user_id=user_id
        )
        
        # Format suggestions for frontend
        suggestions = []
        next_topics = recommendations.get("next_recommended", [])
        
        for topic in next_topics[:limit]:
            suggestions.append({
                "topic_name": topic["name"],
                "description": topic.get("description", ""),
                "difficulty_level": topic.get("difficulty_level", 3),
                "reasoning": f"Ready to learn based on your progress in {topic.get('parent_name', 'previous topics')}"
            })
        
        return {
            "suggestions": suggestions,
            "total_unlocked": recommendations.get("total_unlocked", 0),
            "message": f"Found {len(suggestions)} learning suggestions for you"
        }
        
    except Exception as e:
        logger.error(f"Error getting learning suggestions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to get learning suggestions"
        )

@router.post("/increase-interest")
async def increase_topic_interest(
    request: InterestUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Increase user's interest in a topic when they actively choose to start learning it
    """
    
    try:
        # Import the dynamic ontology service
        from services.dynamic_ontology_service import dynamic_ontology_service
        
        logger.info(f"Starting interest update for user {request.user_id}, topic {request.topic_id}, action {request.action}")
        
        # Update user interest based on starting learning action
        await dynamic_ontology_service.update_user_interest(
            db=db,
            user_id=request.user_id,
            topic_id=request.topic_id,
            action=request.action,
            time_spent=30  # Give some base time for actively choosing to learn
        )
        
        logger.info(f"Successfully increased interest for user {request.user_id} in topic {request.topic_id}")
        
        return {
            "success": True,
            "topic_id": request.topic_id,
            "message": "Successfully increased topic interest"
        }
        
    except Exception as e:
        logger.error(f"Error increasing interest for topic {request.topic_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to increase topic interest: {str(e)}"
        )