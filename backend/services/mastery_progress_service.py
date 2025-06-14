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
    CORRECT_ANSWERS_PER_LEVEL,
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
        
        # SIMPLIFIED: Only track correct answers per level
        mastery_correct_answers = progress.mastery_questions_answered or {
            "novice": 0, 
            "competent": 0, 
            "proficient": 0, 
            "expert": 0, 
            "master": 0
        }
        
        # Handle migration from old complex format to simple format
        if isinstance(mastery_correct_answers.get(current_level.value, 0), dict):
            # Convert from {"total": X, "correct": Y} to just Y
            old_format = mastery_correct_answers
            mastery_correct_answers = {
                "novice": 0, 
                "competent": 0, 
                "proficient": 0, 
                "expert": 0, 
                "master": 0
            }
            for level, data in old_format.items():
                if isinstance(data, dict) and "correct" in data:
                    mastery_correct_answers[level] = data["correct"]
                elif isinstance(data, int):
                    mastery_correct_answers[level] = data
        
        # Get correct answers at current level
        correct_at_level = mastery_correct_answers.get(current_level.value, 0)
        
        progress_info = get_mastery_progress(correct_at_level, current_level)
        
        return {
            "current_level": current_level.value,
            "next_level": get_next_mastery_level(current_level).value if get_next_mastery_level(current_level) else None,
            "correct_answers_at_level": correct_at_level,
            "progress_to_next": progress_info,
            "mastery_correct_answers": mastery_correct_answers,
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
        
        # SIMPLIFIED: Only track correct answers per level (wrong answers don't matter!)
        mastery_correct_answers = progress.mastery_questions_answered or {
            "novice": 0, 
            "competent": 0, 
            "proficient": 0, 
            "expert": 0, 
            "master": 0
        }
        
        current_level = MasteryLevel(progress.current_mastery_level)
        
        # Handle migration from old complex format to simple format
        if isinstance(mastery_correct_answers.get(current_level.value, 0), dict):
            print(f"🔄 Migrating mastery format to simplified version for user {user_id}")
            old_format = mastery_correct_answers
            mastery_correct_answers = {
                "novice": 0, 
                "competent": 0, 
                "proficient": 0, 
                "expert": 0, 
                "master": 0
            }
            for level, data in old_format.items():
                if isinstance(data, dict) and "correct" in data:
                    mastery_correct_answers[level] = data["correct"]
                elif isinstance(data, int):
                    mastery_correct_answers[level] = data
        
        # Record the answer at the CURRENT level first
        if is_correct:
            mastery_correct_answers[current_level.value] = mastery_correct_answers.get(current_level.value, 0) + 1
        
        # Now check for advancement AFTER recording the answer
        correct_answers_at_level = mastery_correct_answers.get(current_level.value, 0)
        
        progress.mastery_questions_answered = mastery_correct_answers
        
        # Force SQLAlchemy to detect the JSON field change
        from sqlalchemy.orm import attributes
        attributes.flag_modified(progress, "mastery_questions_answered")
        
        # Re-calculate correct answers at current level after recording
        correct_answers_at_level = mastery_correct_answers.get(current_level.value, 0)
        
        print(f"🔍 Mastery tracking: User {user_id}, Topic {topic_id}, Level {current_level.value}, Correct answers: {correct_answers_at_level}")
        
        overall_accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        required_correct = CORRECT_ANSWERS_PER_LEVEL.get(current_level, 8)
        
        print(f"🎯 Advancement check: {correct_answers_at_level}/{required_correct} correct answers at {current_level.value}, overall accuracy {overall_accuracy:.2%}")
        
        # Check for mastery level advancement
        advanced = False
        new_level = current_level
        
        if can_advance_mastery(correct_answers_at_level, current_level):
            next_level = get_next_mastery_level(current_level)
            if next_level:
                progress.current_mastery_level = next_level.value
                progress.mastery_level = next_level.value
                new_level = next_level
                advanced = True
                
                # Initialize the new level with 0 correct answers
                mastery_correct_answers[next_level.value] = 0
                progress.mastery_questions_answered = mastery_correct_answers
                attributes.flag_modified(progress, "mastery_questions_answered")
                
                print(f"🎉 LEVEL UP! {current_level.value} → {new_level.value}")
        
        # Update tree navigation capability
        if new_level.value in [TREE_NAVIGATION_THRESHOLD.value, MasteryLevel.PROFICIENT.value, MasteryLevel.EXPERT.value, MasteryLevel.MASTER.value]:
            progress.proficiency_threshold_met = True
        
        await db.commit()
        
        # Calculate correct answers needed for next level if not advanced
        correct_answers_needed = 0
        if not advanced and new_level != MasteryLevel.MASTER:
            required_correct = CORRECT_ANSWERS_PER_LEVEL[new_level]
            current_correct = mastery_correct_answers.get(new_level.value, 0)
            correct_answers_needed = max(0, required_correct - current_correct)
        
        return {
            "advanced": advanced,
            "old_level": mastery_level.value,  # Use the original level passed in
            "new_level": new_level.value,
            "current_level": new_level.value,  # Add current_level for frontend consistency
            "correct_answers_at_level": mastery_correct_answers.get(new_level.value, 0),
            "correct_answers_needed": correct_answers_needed,
            "accuracy": overall_accuracy,
            "can_navigate_tree": progress.proficiency_threshold_met
        }
    
    async def get_recommended_mastery_level(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> MasteryLevel:
        """Get recommended mastery level for next question (simplified - only correct answers matter!)"""
        
        progress = await self._get_or_create_progress(db, user_id, topic_id)
        current_level = MasteryLevel(progress.current_mastery_level)
        
        # SIMPLIFIED: Only track correct answers per level
        mastery_correct_answers = progress.mastery_questions_answered or {
            "novice": 0, 
            "competent": 0, 
            "proficient": 0, 
            "expert": 0, 
            "master": 0
        }
        
        # Handle migration from old complex format to simple format
        if isinstance(mastery_correct_answers.get(current_level.value, 0), dict):
            old_format = mastery_correct_answers
            mastery_correct_answers = {
                "novice": 0, 
                "competent": 0, 
                "proficient": 0, 
                "expert": 0, 
                "master": 0
            }
            for level, data in old_format.items():
                if isinstance(data, dict) and "correct" in data:
                    mastery_correct_answers[level] = data["correct"]
                elif isinstance(data, int):
                    mastery_correct_answers[level] = data
        
        correct_at_current = mastery_correct_answers.get(current_level.value, 0)
        
        # If they can advance, move to next level
        if can_advance_mastery(correct_at_current, current_level):
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
                "correct_answers_at_level": mastery_info["correct_answers_at_level"],
                "mastery_correct_answers": mastery_info["mastery_correct_answers"],
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
                mastery_questions_answered={
                    "novice": 0, 
                    "competent": 0, 
                    "proficient": 0, 
                    "expert": 0, 
                    "master": 0
                },
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
        
        mastery_correct_answers = progress.mastery_questions_answered or {
            "novice": 0, 
            "competent": 0, 
            "proficient": 0, 
            "expert": 0, 
            "master": 0
        }
        
        # Handle migration from old complex format if needed
        if isinstance(mastery_correct_answers.get(current_level.value, 0), dict):
            old_format = mastery_correct_answers
            mastery_correct_answers = {
                "novice": 0, 
                "competent": 0, 
                "proficient": 0, 
                "expert": 0, 
                "master": 0
            }
            for level, data in old_format.items():
                if isinstance(data, dict) and "correct" in data:
                    mastery_correct_answers[level] = data["correct"]
                elif isinstance(data, int):
                    mastery_correct_answers[level] = data
        
        correct_answers_at_current = mastery_correct_answers.get(current_level.value, 0)
        overall_accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        
        # Calculate correct answers needed for next level (simplified!)
        correct_answers_needed = 0
        if current_level != MasteryLevel.MASTER:
            required_correct = CORRECT_ANSWERS_PER_LEVEL[current_level]
            correct_answers_needed = max(0, required_correct - correct_answers_at_current)
        
        return {
            "advanced": False,  # No advancement since this is just status
            "old_level": current_level.value,
            "new_level": current_level.value,
            "current_level": current_level.value,
            "correct_answers_at_level": correct_answers_at_current,
            "correct_answers_needed": correct_answers_needed,
            "accuracy": overall_accuracy,
            "can_navigate_tree": progress.proficiency_threshold_met
        }