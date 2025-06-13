"""
Learning Progress Calculator - Handles user progress calculations and updates
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.logging_config import logger

from db.models import UserSkillProgress, Topic


class LearningProgressCalculator:
    """
    Centralized service for calculating and updating user learning progress
    """
    
    def __init__(self):
        self.difficulty_weights = {
            1: 0.5, 2: 0.6, 3: 0.7, 4: 0.8, 5: 1.0,
            6: 1.2, 7: 1.4, 8: 1.6, 9: 1.8, 10: 2.0
        }
    
    async def update_adaptive_user_progress(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        is_correct: bool, 
        question_difficulty: int
    ) -> float:
        """
        Update user progress for adaptive learning with difficulty-based adjustments
        Returns the learning progress delta
        """
        # Get current progress
        progress_result = await db.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        if not progress:
            # Create new progress entry
            progress = UserSkillProgress(
                user_id=user_id,
                topic_id=topic_id,
                skill_level=0.0,
                confidence=0.0,
                questions_answered=0,
                correct_answers=0,
                mastery_level="novice",
                is_unlocked=True
            )
            db.add(progress)
            await db.flush()
        
        # Calculate progress delta based on difficulty and correctness
        difficulty_weight = self.difficulty_weights.get(question_difficulty, 1.0)
        
        if is_correct:
            # Positive progress, scaled by difficulty
            learning_delta = 0.1 * difficulty_weight
            confidence_delta = 0.05 * difficulty_weight
        else:
            # Small negative progress to encourage learning
            learning_delta = -0.02 * difficulty_weight
            confidence_delta = -0.01 * difficulty_weight
        
        # Update progress values
        old_skill_level = progress.skill_level or 0.0
        old_confidence = progress.confidence or 0.0
        
        progress.skill_level = max(0.0, min(10.0, old_skill_level + learning_delta))
        progress.confidence = max(0.0, min(10.0, old_confidence + confidence_delta))
        
        # Update question tracking
        progress.questions_answered = (progress.questions_answered or 0) + 1
        if is_correct:
            progress.correct_answers = (progress.correct_answers or 0) + 1
        
        # Update mastery level based on skill progression
        progress.mastery_level = self._calculate_mastery_level(
            progress.skill_level, progress.confidence
        )
        
        await db.commit()
        
        logger.debug(
            f"Updated progress for user {user_id}, topic {topic_id}: "
            f"skill {old_skill_level:.2f}→{progress.skill_level:.2f}, "
            f"confidence {old_confidence:.2f}→{progress.confidence:.2f}"
        )
        
        return learning_delta
    
    async def get_current_topic_progress(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> Dict:
        """Get current progress information for a topic"""
        progress_result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, Topic.id == UserSkillProgress.topic_id)
            .where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        result = progress_result.first()
        
        if not result:
            # No progress yet - return defaults
            topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
            topic = topic_result.scalar_one_or_none()
            
            return {
                "topic_name": topic.name if topic else "Unknown",
                "skill_level": 0.0,
                "confidence": 0.0,
                "mastery_level": "novice",
                "questions_answered": 0,
                "accuracy": 0.0
            }
        
        progress, topic = result
        accuracy = (progress.correct_answers / progress.questions_answered 
                   if progress.questions_answered > 0 else 0.0)
        
        return {
            "topic_name": topic.name,
            "skill_level": progress.skill_level or 0.0,
            "confidence": progress.confidence or 0.0,
            "mastery_level": progress.mastery_level or "novice",
            "questions_answered": progress.questions_answered or 0,
            "accuracy": accuracy
        }
    
    async def get_topic_mastery_level(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> str:
        """Get the current mastery level for a topic"""
        progress_result = await db.execute(
            select(UserSkillProgress.mastery_level).where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        mastery = progress_result.scalar_one_or_none()
        return mastery or "novice"
    
    def calculate_engagement_signal(
        self, 
        action: str, 
        is_correct: Optional[bool], 
        time_spent: float, 
        difficulty: int
    ) -> float:
        """Calculate engagement signal based on user action and performance"""
        base_signal = 0.5  # Neutral baseline
        
        if action == "skip":
            return 0.1  # Low engagement for skips
        elif action == "answer":
            if is_correct is None:
                return base_signal
            
            # Base correctness factor
            correctness_factor = 0.8 if is_correct else 0.3
            
            # Time factor - optimal time gets bonus
            optimal_time = 30 + (difficulty * 10)  # More time for harder questions
            if 10 <= time_spent <= optimal_time * 1.5:
                time_factor = 1.0
            elif time_spent < 10:
                time_factor = 0.6  # Too fast might indicate guessing
            else:
                time_factor = 0.8  # Taking time is okay
            
            # Difficulty bonus
            difficulty_bonus = 1.0 + (difficulty - 5) * 0.05
            
            engagement = correctness_factor * time_factor * difficulty_bonus
            return max(0.1, min(1.0, engagement))
        
        return base_signal
    
    def _calculate_mastery_level(self, skill_level: float, confidence: float) -> str:
        """Calculate mastery level based on skill and confidence"""
        avg_level = (skill_level + confidence) / 2
        
        if avg_level < 2.0:
            return "novice"
        elif avg_level < 4.0:
            return "beginner"
        elif avg_level < 6.0:
            return "intermediate"
        elif avg_level < 8.0:
            return "advanced"
        else:
            return "expert"


# Global instance
learning_progress_calculator = LearningProgressCalculator()