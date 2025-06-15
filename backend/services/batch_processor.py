"""
Batch processing utilities for efficient database operations during quiz sessions
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from db.models import QuizQuestion, UserSkillProgress, UserTopicInterest
from core.logging_config import logger
from db.connection_manager import connection_manager

class BatchProcessor:
    """
    Handles batch operations for quiz sessions to minimize database round trips
    """
    
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.pending_operations = []
        self.lock = asyncio.Lock()
    
    async def add_operation(self, operation: Dict[str, Any]):
        """Add an operation to the batch queue"""
        async with self.lock:
            self.pending_operations.append(operation)
            
            # Auto-flush if batch size reached
            if len(self.pending_operations) >= self.batch_size:
                await self.flush()
    
    async def flush(self):
        """Execute all pending operations in a single transaction"""
        if not self.pending_operations:
            return
        
        async with self.lock:
            operations = self.pending_operations.copy()
            self.pending_operations.clear()
        
        async with connection_manager.get_session() as db:
            try:
                # Group operations by type
                quiz_questions = []
                skill_updates = []
                interest_updates = []
                
                for op in operations:
                    if op['type'] == 'quiz_question':
                        quiz_questions.append(op['data'])
                    elif op['type'] == 'skill_update':
                        skill_updates.append(op['data'])
                    elif op['type'] == 'interest_update':
                        interest_updates.append(op['data'])
                
                # Batch insert quiz questions
                if quiz_questions:
                    await db.execute(
                        insert(QuizQuestion),
                        quiz_questions
                    )
                
                # Batch update skill progress
                if skill_updates:
                    await self._batch_update_skills(db, skill_updates)
                
                # Batch update interests
                if interest_updates:
                    await self._batch_update_interests(db, interest_updates)
                
                await db.commit()
                logger.info(f"Batch processed {len(operations)} operations successfully")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Batch processing failed: {e}")
                raise
    
    async def _batch_update_skills(self, db: AsyncSession, updates: List[Dict]):
        """Batch update user skill progress"""
        # Use PostgreSQL's ON CONFLICT for upsert
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        stmt = pg_insert(UserSkillProgress).values(updates)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'topic_id'],
            set_={
                'mastery_level': stmt.excluded.mastery_level,
                'confidence_score': stmt.excluded.confidence_score,
                'last_practice_date': stmt.excluded.last_practice_date,
                'total_attempts': UserSkillProgress.total_attempts + stmt.excluded.total_attempts,
                'correct_attempts': UserSkillProgress.correct_attempts + stmt.excluded.correct_attempts
            }
        )
        
        await db.execute(stmt)
    
    async def _batch_update_interests(self, db: AsyncSession, updates: List[Dict]):
        """Batch update user topic interests"""
        stmt = pg_insert(UserTopicInterest).values(updates)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'topic_id'],
            set_={
                'interest_score': stmt.excluded.interest_score,
                'confidence': stmt.excluded.confidence,
                'last_interaction': stmt.excluded.last_interaction,
                'interaction_count': UserTopicInterest.interaction_count + 1
            }
        )
        
        await db.execute(stmt)
    
    async def prefetch_quiz_data(
        self, 
        db: AsyncSession,
        user_id: int,
        topic_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Prefetch all necessary data for a quiz session in one go
        """
        from db.models import Topic, Question, UserSkillProgress, UserTopicInterest
        
        result = {}
        
        # Fetch topics
        topics_result = await db.execute(
            select(Topic).where(Topic.id.in_(topic_ids))
        )
        result['topics'] = {t.id: t for t in topics_result.scalars().all()}
        
        # Fetch user skill progress
        skills_result = await db.execute(
            select(UserSkillProgress)
            .where(UserSkillProgress.user_id == user_id)
            .where(UserSkillProgress.topic_id.in_(topic_ids))
        )
        result['skills'] = {s.topic_id: s for s in skills_result.scalars().all()}
        
        # Fetch user interests
        interests_result = await db.execute(
            select(UserTopicInterest)
            .where(UserTopicInterest.user_id == user_id)
            .where(UserTopicInterest.topic_id.in_(topic_ids))
        )
        result['interests'] = {i.topic_id: i for i in interests_result.scalars().all()}
        
        # Fetch available questions
        questions_result = await db.execute(
            select(Question)
            .where(Question.topic_id.in_(topic_ids))
            .where(Question.is_active == True)
        )
        result['questions'] = list(questions_result.scalars().all())
        
        return result
    
    async def batch_log_quiz_activity(
        self,
        activities: List[Dict[str, Any]]
    ):
        """
        Log multiple quiz activities efficiently
        """
        # Group by activity type for efficient processing
        grouped = {}
        for activity in activities:
            activity_type = activity.get('type', 'unknown')
            if activity_type not in grouped:
                grouped[activity_type] = []
            grouped[activity_type].append(activity)
        
        # Process each group
        for activity_type, items in grouped.items():
            if activity_type == 'question_answered':
                await self._log_answers(items)
            elif activity_type == 'session_progress':
                await self._log_progress(items)
            # Add more activity types as needed
    
    async def _log_answers(self, answers: List[Dict]):
        """Log batch of quiz answers"""
        # Implementation for logging answers
        operations = []
        for answer in answers:
            operations.append({
                'type': 'quiz_question',
                'data': {
                    'quiz_session_id': answer['session_id'],
                    'question_id': answer['question_id'],
                    'user_answer': answer['answer'],
                    'is_correct': answer['is_correct'],
                    'time_spent': answer['time_spent']
                }
            })
        
        for op in operations:
            await self.add_operation(op)
    
    async def _log_progress(self, progress_items: List[Dict]):
        """Log batch of progress updates"""
        operations = []
        for item in progress_items:
            operations.append({
                'type': 'skill_update',
                'data': {
                    'user_id': item['user_id'],
                    'topic_id': item['topic_id'],
                    'mastery_level': item['mastery_level'],
                    'confidence_score': item['confidence_score'],
                    'last_practice_date': item['timestamp'],
                    'total_attempts': item.get('attempts', 1),
                    'correct_attempts': item.get('correct', 0)
                }
            })
        
        for op in operations:
            await self.add_operation(op)


# Global batch processor instance
batch_processor = BatchProcessor()

# Context manager for batch operations
class BatchContext:
    """Context manager for batch operations"""
    
    def __init__(self, processor: BatchProcessor = None):
        self.processor = processor or batch_processor
    
    async def __aenter__(self):
        return self.processor
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Always flush on exit
        await self.processor.flush()
        return False


# Decorator for batch operations
def batch_operation(batch_size: int = 10):
    """Decorator to batch database operations"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            processor = BatchProcessor(batch_size)
            kwargs['batch_processor'] = processor
            
            try:
                result = await func(*args, **kwargs)
                await processor.flush()
                return result
            except Exception as e:
                logger.error(f"Batch operation failed: {e}")
                raise
        
        return wrapper
    return decorator