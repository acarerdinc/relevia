from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Union
from db.database import get_db
from db.connection_manager import connection_manager, with_retry
from services.quiz_service import quiz_engine

router = APIRouter()

class StartQuizRequest(BaseModel):
    topic_id: int
    user_id: int = 1  # For now, default user

class SubmitAnswerRequest(BaseModel):
    quiz_question_id: int
    answer: Union[str, int, None] = None  # Allow string, int, or None
    time_spent: int = 0
    action: str = "answer"  # answer, teach_me, skip

@router.post("/start")
async def start_quiz(request: StartQuizRequest):
    """Start a new quiz session with retry logic"""
    async with connection_manager.get_session() as db:
        try:
            session = await quiz_engine.start_quiz_session(
                db=db,
                user_id=request.user_id,
                topic_id=request.topic_id
            )
            await db.commit()
            
            return {
                "session_id": session.id,
                "topic_id": session.topic_id,
                "message": "Quiz started successfully"
            }
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/question/{session_id}")
@with_retry(timeout=10.0)
async def get_question(session_id: int, db: AsyncSession = None):
    """Get next question for the quiz with retry logic"""
    try:
        question = await quiz_engine.get_next_question(db=db, session_id=session_id)
        
        if not question:
            raise HTTPException(status_code=404, detail="Quiz session not found")
        
        return question
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
@with_retry(timeout=15.0)
async def submit_answer(request: SubmitAnswerRequest, db: AsyncSession = None):
    """Submit answer and get feedback with retry logic"""
    try:
        result = await quiz_engine.submit_answer(
            db=db,
            quiz_question_id=request.quiz_question_id,
            user_answer=request.answer,
            time_spent=request.time_spent,
            action=request.action
        )
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
@with_retry(timeout=5.0)
async def get_session_info(session_id: int, db: AsyncSession = None):
    """Get quiz session information with retry logic"""
    from sqlalchemy import select
    from db.models import QuizSession, Topic
    
    try:
        result = await db.execute(
            select(QuizSession, Topic)
            .join(Topic, QuizSession.topic_id == Topic.id)
            .where(QuizSession.id == session_id)
        )
        
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session, topic = row
        
        return {
            "session_id": session.id,
            "topic": topic.name,
            "total_questions": session.total_questions,
            "correct_answers": session.correct_answers,
            "accuracy": session.correct_answers / session.total_questions if session.total_questions > 0 else 0,
            "started_at": session.started_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))