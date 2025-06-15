"""
Adaptive Learning API - Simplified endpoints for exploration/exploitation learning
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Union
import asyncio
from core.logging_config import logger

from db.database import get_db
from db.connection_manager import connection_manager, with_retry
from db.models import User
from api.routes.auth import get_current_user, get_current_user_light
from services.adaptive_quiz_service import adaptive_quiz_service

router = APIRouter(prefix="/adaptive", tags=["adaptive_learning"])


class AdaptiveAnswerRequest(BaseModel):
    quiz_question_id: int
    answer: Union[str, int, None] = None  # Allow string, int, or None
    time_spent: int = 0
    action: str = "answer"  # answer, teach_me, skip


@router.post("/start")
@with_retry(timeout=10.0)
async def start_adaptive_learning(
    user_id: int,
    db: AsyncSession = None
):
    """
    Start an adaptive learning session with retry logic
    No topic selection required - system intelligently selects best content
    """
    try:
        session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id)
        return session_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/question/{session_id}")
@with_retry(timeout=10.0)
async def get_next_question(
    session_id: int,
    db: AsyncSession = None
):
    """
    Get next question using adaptive exploration/exploitation algorithm with retry logic
    Automatically selects the best question across all topics
    """
    try:
        question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
        
        if not question_data or "error" in question_data:
            # Return proper error structure instead of raising HTTP exception
            return {
                "error": question_data.get("error", "No more questions available"),
                "suggestion": question_data.get("suggestion", "session_complete"),
                "message": "Great job! You've completed this learning session."
            }
        
        return question_data
    except Exception as e:
        # Return error structure instead of raising HTTP exception
        return {
            "error": f"Failed to get question: {str(e)}",
            "suggestion": "try_again",
            "message": "Something went wrong. Please try again."
        }


@router.post("/answer")
@with_retry(timeout=15.0)
async def submit_answer(
    request: AdaptiveAnswerRequest,
    db: AsyncSession = None
):
    """
    Submit answer with full adaptive learning pipeline and retry logic
    Handles answer evaluation, interest tracking, and discovery
    """
    try:
        response = await adaptive_quiz_service.submit_adaptive_answer(
            db=db,
            quiz_question_id=request.quiz_question_id,
            user_answer=request.answer,
            time_spent=request.time_spent,
            action=request.action
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")


@router.get("/dashboard/{user_id}")
@with_retry(timeout=10.0)
async def get_learning_dashboard(
    user_id: int,
    db: AsyncSession = None
):
    """
    Get comprehensive learning dashboard for simplified UI with retry logic
    Shows learning state, interests, achievements, and recommendations
    """
    try:
        dashboard_data = await adaptive_quiz_service.get_learning_dashboard(db, user_id)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/continue")
async def continue_learning(
    current_user: dict = Depends(get_current_user_light)
):
    """
    Smart continue learning endpoint - ultra-simplified version
    Returns session info immediately without database operations
    """
    try:
        # Just create session synchronously to avoid any async issues
        from db.models import QuizSession
        import random
        
        # Generate a temporary session ID
        temp_session_id = random.randint(1000, 9999)
        
        # Return immediately without database operations
        return {
            "session": {
                "session_id": temp_session_id,
                "session_type": "adaptive",
                "user_id": current_user["id"],
                "temporary": True
            },
            "message": "Ready to learn!",
            "next_action": "call_start_session_endpoint"
        }
        
    except Exception as e:
        logger.error(f"Error in continue learning: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to prepare session: {str(e)}")


@router.get("/insights/{user_id}")
@with_retry(timeout=10.0)
async def get_learning_insights(
    user_id: int,
    db: AsyncSession = None
):
    """
    Get detailed learning insights and analytics with retry logic
    For power users who want to see their learning patterns
    """
    try:
        from services.adaptive_interest_tracker import adaptive_interest_tracker
        from services.adaptive_question_selector import adaptive_question_selector
        
        # Get comprehensive insights
        interest_insights = await adaptive_interest_tracker.get_interest_insights(db, user_id)
        exploration_stats = await adaptive_question_selector.get_exploration_stats(db, user_id)
        
        return {
            "interests": interest_insights,
            "exploration": exploration_stats,
            "summary": {
                "learning_style": interest_insights.get("learning_patterns", {}).get("learning_style", "balanced"),
                "exploration_coverage": exploration_stats.get("exploration_coverage", 0),
                "discovery_rate": exploration_stats.get("discovery_rate", 0),
                "engagement_diversity": exploration_stats.get("engagement_diversity", 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.post("/feedback")
@with_retry(timeout=5.0)
async def submit_session_feedback(
    session_id: int,
    rating: int,  # 1-5 stars
    feedback: Optional[str] = None,
    db: AsyncSession = None
):
    """
    Submit feedback about the adaptive learning session with retry logic
    Used to improve the exploration/exploitation algorithm
    """
    try:
        # For now, just acknowledge feedback
        # In future, this could feed back into the bandit algorithm
        return {
            "message": "Thank you for your feedback!",
            "rating": rating,
            "session_id": session_id,
            "improvement_noted": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process feedback: {str(e)}")


# Legacy compatibility endpoints (redirect to adaptive)
@router.get("/legacy/next-question/{user_id}")
async def legacy_get_question(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Legacy endpoint that redirects to adaptive learning
    Maintains backward compatibility
    """
    return await continue_learning(user_id, db)