"""
Quiz Session Manager - Handles session creation, management, and validation
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from core.logging_config import logger

from db.models import QuizSession, QuizQuestion, Question, Topic


class QuizSessionManager:
    """
    Centralized service for managing quiz sessions
    """
    
    def __init__(self):
        self.session_timeout_minutes = 30
    
    async def create_adaptive_session(self, db: AsyncSession, user_id: int) -> QuizSession:
        """Create a new adaptive learning session"""
        session = QuizSession(
            user_id=user_id,
            topic_id=None,  # Adaptive sessions are cross-topic
            started_at=datetime.now(timezone.utc),
            total_questions=0,
            correct_answers=0,
            session_type="adaptive"
        )
        
        db.add(session)
        await db.commit()
        
        logger.info(f"Created adaptive session {session.id} for user {user_id}")
        return session
    
    async def get_session(self, db: AsyncSession, session_id: int) -> Optional[QuizSession]:
        """Get session by ID with validation"""
        result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        # Check if session is still active
        if self._is_session_expired(session):
            logger.info(f"Session {session_id} has expired")
            return None
        
        return session
    
    async def create_quiz_question_link(
        self, 
        db: AsyncSession, 
        session_id: int, 
        question_id: int
    ) -> QuizQuestion:
        """Create a link between quiz session and question"""
        quiz_question = QuizQuestion(
            quiz_session_id=session_id,
            question_id=question_id
        )
        
        db.add(quiz_question)
        await db.commit()
        
        return quiz_question
    
    async def update_session_stats(
        self, 
        db: AsyncSession, 
        session: QuizSession, 
        is_correct: Optional[bool]
    ):
        """Update session statistics after a question is answered"""
        if session.total_questions is None:
            session.total_questions = 0
        if session.correct_answers is None:
            session.correct_answers = 0
            
        session.total_questions += 1
        if is_correct:
            session.correct_answers += 1
        
        await db.commit()
        logger.debug(f"Updated session {session.id} stats: {session.correct_answers}/{session.total_questions}")
    
    async def get_session_with_question(
        self, 
        db: AsyncSession, 
        quiz_question_id: int
    ) -> Optional[tuple[QuizSession, QuizQuestion, Question, Topic]]:
        """Get session along with question and topic data"""
        result = await db.execute(
            select(QuizSession, QuizQuestion, Question, Topic)
            .join(QuizQuestion, QuizQuestion.quiz_session_id == QuizSession.id)
            .join(Question, Question.id == QuizQuestion.question_id)
            .join(Topic, Topic.id == Question.topic_id)
            .where(QuizQuestion.id == quiz_question_id)
        )
        
        return result.first()
    
    def get_session_progress_data(self, session: QuizSession) -> Dict:
        """Get session progress information"""
        total = session.total_questions or 0
        correct = session.correct_answers or 0
        
        return {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": correct / total if total > 0 else 0
        }
    
    def _is_session_expired(self, session: QuizSession) -> bool:
        """Check if session has expired based on timeout"""
        if not session.started_at:
            return True
        
        # Ensure started_at is timezone-aware
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        
        elapsed = datetime.now(timezone.utc) - started_at
        return elapsed.total_seconds() > (self.session_timeout_minutes * 60)


# Global instance
quiz_session_manager = QuizSessionManager()