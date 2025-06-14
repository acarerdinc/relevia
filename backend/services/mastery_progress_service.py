"""
Mastery Progress Service - Manages user progress through mastery levels
"""

from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.models import UserSkillProgress, Topic
from core.mastery_levels import (
    MasteryLevel, 
    get_next_mastery_level, 
    can_advance_mastery, 
    get_mastery_progress,
    QUESTIONS_PER_LEVEL,
    ACCURACY_THRESHOLD,
    TREE_NAVIGATION_THRESHOLD
)
import json

class MasteryProgressService:
    """Manages user mastery progression within topics"""
    
    async def get_user_mastery(self, db: AsyncSession, user_id: int, topic_id: int) -> Dict:
        """Get user's current mastery status for a topic"""
        
        # Get or create progress record
        progress = await self._get_or_create_progress(db, user_id, topic_id)
        
        current_level = MasteryLevel(progress.current_mastery_level)
        mastery_questions = progress.mastery_questions_answered or {
            "novice": {"total": 0, "correct": 0}, 
            "competent": {"total": 0, "correct": 0}, 
            "proficient": {"total": 0, "correct": 0}, 
            "expert": {"total": 0, "correct": 0}, 
            "master": {"total": 0, "correct": 0}
        }
        
        # Handle migration from old format if needed
        if isinstance(mastery_questions.get(current_level.value, 0), int):
            old_mastery = mastery_questions
            mastery_questions = {
                "novice": {"total": 0, "correct": 0}, 
                "competent": {"total": 0, "correct": 0}, 
                "proficient": {"total": 0, "correct": 0}, 
                "expert": {"total": 0, "correct": 0}, 
                "master": {"total": 0, "correct": 0}
            }
            for level, count in old_mastery.items():
                if isinstance(count, int) and count > 0:
                    mastery_questions[level] = {"total": count, "correct": count}
        
        # Calculate progress for current level
        level_stats = mastery_questions.get(current_level.value, {"total": 0, "correct": 0})
        questions_at_level = level_stats["total"]
        correct_at_level = level_stats["correct"]
        
        progress_info = get_mastery_progress(questions_at_level, current_level)
        
        return {
            "current_level": current_level.value,
            "next_level": get_next_mastery_level(current_level).value if get_next_mastery_level(current_level) else None,
            "questions_answered_at_level": questions_at_level,
            "correct_answers_at_level": correct_at_level,
            "progress_to_next": progress_info,
            "mastery_questions_breakdown": mastery_questions,
            "can_navigate_tree": current_level.value in [level.value for level in [TREE_NAVIGATION_THRESHOLD, MasteryLevel.PROFICIENT, MasteryLevel.EXPERT, MasteryLevel.MASTER]],
            "total_questions": progress.questions_answered,
            "total_correct": progress.correct_answers
        }
    
    async def record_mastery_answer(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        mastery_level: MasteryLevel,
        is_correct: bool
    ) -> Dict:
        """Record an answer at a specific mastery level and check for level advancement"""
        
        progress = await self._get_or_create_progress(db, user_id, topic_id)
        
        # Update overall stats
        progress.questions_answered += 1
        if is_correct:
            progress.correct_answers += 1
        
        # Update mastery-specific stats - track BOTH total questions and correct answers per level
        mastery_questions = progress.mastery_questions_answered or {
            "novice": {"total": 0, "correct": 0}, 
            "competent": {"total": 0, "correct": 0}, 
            "proficient": {"total": 0, "correct": 0}, 
            "expert": {"total": 0, "correct": 0}, 
            "master": {"total": 0, "correct": 0}
        }
        
        # Handle migration from old format (just numbers) to new format (objects)
        current_level = MasteryLevel(progress.current_mastery_level)
        
        # Migrate old format if needed
        if isinstance(mastery_questions.get(current_level.value, 0), int):
            print(f"🔄 Migrating old mastery format for user {user_id}")
            old_mastery = mastery_questions
            mastery_questions = {
                "novice": {"total": 0, "correct": 0}, 
                "competent": {"total": 0, "correct": 0}, 
                "proficient": {"total": 0, "correct": 0}, 
                "expert": {"total": 0, "correct": 0}, 
                "master": {"total": 0, "correct": 0}
            }
            # Migrate old correct counts as both total and correct (assuming 100% accuracy for old data)
            for level, count in old_mastery.items():
                if isinstance(count, int) and count > 0:
                    mastery_questions[level] = {"total": count, "correct": count}
        
        # Increment counters for current mastery level
        level_stats = mastery_questions.get(current_level.value, {"total": 0, "correct": 0})
        level_stats["total"] += 1
        if is_correct:
            level_stats["correct"] += 1
        
        mastery_questions[current_level.value] = level_stats
        progress.mastery_questions_answered = mastery_questions
        
        # Force SQLAlchemy to detect the JSON field change
        from sqlalchemy.orm import attributes
        attributes.flag_modified(progress, "mastery_questions_answered")
        
        # Check for mastery level advancement
        questions_at_current = level_stats["total"]
        correct_answers_at_level = level_stats["correct"]
        
        print(f"🔍 Mastery tracking: User {user_id}, Topic {topic_id}, Level {current_level.value}, Total: {questions_at_current}, Correct: {correct_answers_at_level}")
        
        overall_accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        level_accuracy = correct_answers_at_level / questions_at_current if questions_at_current > 0 else 0
        
        print(f"🎯 Advancement check: {correct_answers_at_level}/{questions_at_current} ({level_accuracy:.1%}) at {current_level.value}, overall accuracy {overall_accuracy:.2%}")
        
        advanced = False
        new_level = current_level
        
        if can_advance_mastery(questions_at_current, correct_answers_at_level, current_level):
            next_level = get_next_mastery_level(current_level)
            if next_level:
                progress.current_mastery_level = next_level.value
                progress.mastery_level = next_level.value  # Update both fields
                new_level = next_level
                advanced = True
                
                # Start tracking at new level (this question counts for the new level)
                next_level_stats = mastery_questions.get(next_level.value, {"total": 0, "correct": 0})
                next_level_stats["total"] += 1
                if is_correct:
                    next_level_stats["correct"] += 1
                mastery_questions[next_level.value] = next_level_stats
                progress.mastery_questions_answered = mastery_questions
                
                # Force SQLAlchemy to detect the JSON field change
                from sqlalchemy.orm import attributes
                attributes.flag_modified(progress, "mastery_questions_answered")
                
                print(f"🎉 LEVEL UP! {current_level.value} → {next_level.value}, starting fresh at {next_level.value} with 1 question")
        
        # Update tree navigation capability
        if new_level.value in [TREE_NAVIGATION_THRESHOLD.value, MasteryLevel.PROFICIENT.value, MasteryLevel.EXPERT.value, MasteryLevel.MASTER.value]:
            progress.proficiency_threshold_met = True
        
        await db.commit()
        
        # Calculate questions needed for next level if not advanced
        questions_needed = 0
        if not advanced and new_level != MasteryLevel.MASTER:
            required_questions = QUESTIONS_PER_LEVEL[new_level]
            questions_needed = max(0, required_questions - questions_at_current)
        
        return {
            "advanced": advanced,
            "old_level": current_level.value,
            "new_level": new_level.value,
            "current_level": new_level.value,  # Add current_level for frontend consistency
            "questions_at_level": questions_at_current,
            "questions_needed": questions_needed,
            "accuracy": overall_accuracy,
            "can_navigate_tree": progress.proficiency_threshold_met
        }
    
    async def get_recommended_mastery_level(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> MasteryLevel:
        """Get recommended mastery level for next question"""
        
        progress = await self._get_or_create_progress(db, user_id, topic_id)
        current_level = MasteryLevel(progress.current_mastery_level)
        
        mastery_questions = progress.mastery_questions_answered or {
            "novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0
        }
        
        questions_at_current = mastery_questions.get(current_level.value, 0)
        required_questions = QUESTIONS_PER_LEVEL.get(current_level, 8)
        
        # If user hasn't completed enough questions at current level, stay there
        if questions_at_current < required_questions:
            return current_level
        
        # If they can advance, move to next level
        accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        if can_advance_mastery(questions_at_current, progress.correct_answers, current_level):
            next_level = get_next_mastery_level(current_level)
            return next_level if next_level else current_level
        
        # Stay at current level for more practice
        return current_level
    
    async def get_mastery_overview(self, db: AsyncSession, user_id: int) -> Dict:
        """Get overview of user's mastery across all topics"""
        
        result = await db.execute(
            select(UserSkillProgress, Topic.name)
            .join(Topic)
            .where(UserSkillProgress.user_id == user_id)
            .where(UserSkillProgress.current_mastery_level.isnot(None))
        )
        
        topics_mastery = []
        level_counts = {"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}
        
        for progress, topic_name in result:
            mastery_info = await self.get_user_mastery(db, user_id, progress.topic_id)
            topics_mastery.append({
                "topic_name": topic_name,
                "topic_id": progress.topic_id,
                "current_level": progress.current_mastery_level,
                "progress": mastery_info["progress_to_next"],
                "can_navigate": mastery_info["can_navigate_tree"]
            })
            
            level_counts[progress.current_mastery_level] += 1
        
        return {
            "topics_mastery": topics_mastery,
            "level_distribution": level_counts,
            "total_topics": len(topics_mastery)
        }
    
    async def _get_or_create_progress(self, db: AsyncSession, user_id: int, topic_id: int) -> UserSkillProgress:
        """Get existing progress or create new one"""
        
        result = await db.execute(
            select(UserSkillProgress)
            .where(UserSkillProgress.user_id == user_id)
            .where(UserSkillProgress.topic_id == topic_id)
        )
        
        progress = result.scalar_one_or_none()
        
        if not progress:
            progress = UserSkillProgress(
                user_id=user_id,
                topic_id=topic_id,
                skill_level=0.5,
                confidence=0.5,
                questions_answered=0,
                correct_answers=0,
                mastery_level="novice",
                current_mastery_level="novice",
                mastery_questions_answered={"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0},
                is_unlocked=True,
                proficiency_threshold_met=False
            )
            db.add(progress)
            await db.flush()
        
        return progress
    
    async def get_current_mastery_status(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> Dict:
        """Get current mastery status without updating progress"""
        
        progress = await self._get_or_create_progress(db, user_id, topic_id)
        current_level = MasteryLevel(progress.current_mastery_level)
        
        mastery_questions = progress.mastery_questions_answered or {
            "novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0
        }
        
        questions_at_current = mastery_questions.get(current_level.value, 0)
        overall_accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        
        # Calculate questions needed for next level
        questions_needed = 0
        if current_level != MasteryLevel.MASTER:
            required_questions = QUESTIONS_PER_LEVEL[current_level]
            questions_needed = max(0, required_questions - questions_at_current)
        
        return {
            "advanced": False,  # No advancement since this is just status
            "old_level": current_level.value,
            "new_level": current_level.value,
            "current_level": current_level.value,
            "questions_at_level": questions_at_current,
            "questions_needed": questions_needed,
            "accuracy": overall_accuracy,
            "can_navigate_tree": progress.proficiency_threshold_met
        }