"""
Adaptive Learning API - Simplified endpoints for exploration/exploitation learning
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Union

from db.database import get_db
from services.adaptive_quiz_service import adaptive_quiz_service

router = APIRouter(prefix="/adaptive", tags=["adaptive_learning"])


class AdaptiveAnswerRequest(BaseModel):
    quiz_question_id: int
    answer: Union[str, int, None] = None  # Allow string, int, or None
    time_spent: int = 0
    action: str = "answer"  # answer, teach_me, skip


@router.post("/start")
async def start_adaptive_learning(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Start an adaptive learning session
    No topic selection required - system intelligently selects best content
    """
    try:
        session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id)
        return session_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.get("/question/{session_id}")
async def get_next_question(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get next question using adaptive exploration/exploitation algorithm
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
async def submit_answer(
    request: AdaptiveAnswerRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit answer with full adaptive learning pipeline
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
async def get_learning_dashboard(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive learning dashboard for simplified UI
    Shows learning state, interests, achievements, and recommendations
    """
    try:
        dashboard_data = await adaptive_quiz_service.get_learning_dashboard(db, user_id)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/continue/{user_id}")
async def continue_learning(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Smart continue learning endpoint
    Automatically starts session and gets first question in one call
    """
    try:
        # Start adaptive session
        session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id)
        session_id = session_data["session_id"]
        
        # Get first question
        question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
        
        if not question_data or "error" in question_data:
            # Return session info with suggestion to explore
            return {
                **session_data,
                "error": "no_questions_available",
                "suggestion": "explore_new_areas", 
                "message": "Ready to learn! Let's start by exploring some foundational topics."
            }
        
        # Start prefetching second question immediately for faster UX
        import asyncio
        asyncio.create_task(adaptive_quiz_service._prefetch_next_question(user_id, session_id))
        
        # Return combined session + question data
        return {
            "session": session_data,
            "question": question_data,
            "ready_to_learn": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to continue learning: {str(e)}")


@router.get("/insights/{user_id}")
async def get_learning_insights(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed learning insights and analytics
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
async def submit_session_feedback(
    session_id: int,
    rating: int,  # 1-5 stars
    feedback: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback about the adaptive learning session
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