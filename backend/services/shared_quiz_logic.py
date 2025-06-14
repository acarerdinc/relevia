"""
Shared Quiz Logic - Common functionality between focused and adaptive quiz modes
"""
import asyncio
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from db.models import UserSkillProgress, QuizQuestion, Question, QuizSession
from core.mastery_levels import MasteryLevel
from services.mastery_progress_service import MasteryProgressService
from services.dynamic_ontology_service import dynamic_ontology_service


class SharedQuizLogic:
    """
    Shared logic between focused and adaptive quiz modes to ensure consistency
    """
    
    def __init__(self):
        self.mastery_service = MasteryProgressService()
    
    async def process_answer_submission(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        is_correct: bool,
        action: str = "answer"
    ) -> Optional[Dict]:
        """
        Unified answer processing logic used by both focused and adaptive modes
        Returns mastery advancement information
        """
        
        if action != "answer" or is_correct is None:
            return None
            
        # Get current mastery level
        user_progress_result = await db.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        user_progress = user_progress_result.scalar_one_or_none()
        
        if not user_progress:
            return None
            
        # Record mastery answer using current mastery level (not hardcoded)
        current_mastery = MasteryLevel(user_progress.current_mastery_level or "novice")
        mastery_advancement = await self.mastery_service.record_mastery_answer(
            db, user_id, topic_id, current_mastery, is_correct
        )
        
        return mastery_advancement
    
    async def trigger_background_subtopic_generation(
        self,
        user_id: int,
        topic_id: int,
        action: str = "answer",
        is_correct: Optional[bool] = None
    ):
        """
        Unified background subtopic generation logic used by both modes
        """
        
        if action != "answer" or is_correct is None:
            return
            
        # Run topic unlocking as true background task - don't wait for it
        async def background_subtopic_generation():
            try:
                # Create new database session for background task
                from db.database import AsyncSessionLocal
                async with AsyncSessionLocal() as bg_db:
                    await dynamic_ontology_service.check_and_unlock_subtopics(
                        bg_db, user_id, topic_id
                    )
                    print(f"✅ Background subtopic generation completed for user {user_id}, topic {topic_id}")
            except Exception as e:
                print(f"⚠️ Background topic unlock failed for user {user_id}: {e}")
        
        # Start background task without waiting
        asyncio.create_task(background_subtopic_generation())
    
    async def update_user_interests(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        action: str,
        time_spent: float = 0
    ):
        """
        Unified interest tracking logic used by both modes
        """
        
        await dynamic_ontology_service.update_user_interest(
            db, user_id, topic_id, action, time_spent
        )
    
    def calculate_session_progress(self, session: QuizSession) -> Dict:
        """
        Unified session progress calculation
        """
        
        total = session.total_questions or 0
        correct = session.correct_answers or 0
        
        return {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": correct / total if total > 0 else 0
        }
    
    def shuffle_question_options(self, options: list, correct_answer: str, debug_mode: bool = True) -> tuple:
        """
        Unified question shuffling logic with debug mode support
        Returns (shuffled_options, shuffled_correct_answer, debug_correct_index)
        """
        
        debug_correct_index = None
        
        if debug_mode:
            # Don't shuffle in debug mode - keep original order
            shuffled_options = options.copy()
            shuffled_correct = correct_answer
            
            # Find correct option index for frontend highlighting
            for i, option in enumerate(shuffled_options):
                # Check for exact match first
                if option == shuffled_correct or option.strip().lower() == shuffled_correct.strip().lower():
                    debug_correct_index = i
                    break
                # Check for letter-based match (e.g., correct_answer="C" matches "C) text...")
                elif (len(shuffled_correct.strip()) == 1 and 
                      shuffled_correct.strip().upper() in 'ABCD' and
                      option.strip() and 
                      option.strip()[0].upper() == shuffled_correct.strip().upper()):
                    debug_correct_index = i
                    break
        else:
            # Normal mode: Shuffle options to prevent predictable correct answer positions
            import random
            
            # Make a copy to avoid modifying the original
            shuffled_options = options.copy()
            
            # Find the index of the correct answer
            try:
                correct_index = shuffled_options.index(correct_answer)
            except ValueError:
                # If exact match fails, try case-insensitive search
                correct_index = None
                for i, option in enumerate(shuffled_options):
                    if option.strip().lower() == correct_answer.strip().lower():
                        correct_index = i
                        break
                
                # If still not found, return original (don't shuffle to avoid breaking)
                if correct_index is None:
                    print(f"Warning: Correct answer '{correct_answer}' not found in options, skipping shuffle")
                    return options, correct_answer, None
            
            # Create a list of indices and shuffle them
            indices = list(range(len(shuffled_options)))
            random.shuffle(indices)
            
            # Reorder options according to shuffled indices
            shuffled_options = [options[i] for i in indices]
            
            # Find where the correct answer ended up after shuffling
            new_correct_index = indices.index(correct_index)
            shuffled_correct = shuffled_options[new_correct_index]
        
        return shuffled_options, shuffled_correct, debug_correct_index


# Global instance
shared_quiz_logic = SharedQuizLogic()