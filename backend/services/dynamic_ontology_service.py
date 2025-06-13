"""
Dynamic Ontology Service - Handles expanding topic tree based on proficiency and interest
"""
import asyncio
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from datetime import datetime, timedelta

from db.models import (
    Topic, UserSkillProgress, UserInterest, DynamicTopicUnlock,
    LearningGoal, QuizQuestion, Question
)
from services.dynamic_topic_generator import DynamicTopicGenerator

class DynamicOntologyService:
    """
    Manages dynamic topic unlocking and interest-based recommendations
    """
    
    # Proficiency thresholds for unlocking subtopics (BALANCED for meaningful progression)
    PROFICIENCY_THRESHOLDS = {
        "beginner": 0.6,      # 60% accuracy - show basic understanding
        "intermediate": 0.7,  # 70% accuracy - consistent performance
        "advanced": 0.8,      # 80% accuracy - strong grasp
        "expert": 0.9         # 90% accuracy - mastery
    }
    
    # Interest score thresholds (BALANCED for quality signals)
    INTEREST_THRESHOLDS = {
        "high": 0.7,          # Clear, sustained interest
        "medium": 0.4,        # Moderate engagement
        "low": 0.2            # Some interaction
    }
    
    def __init__(self):
        self.min_questions_for_proficiency = 5  # Increased to 5 to prevent premature unlocking during quiz
        self.interest_decay_factor = 0.95  # Interest decays over time
        self.topic_generator = DynamicTopicGenerator()
    
    async def update_user_interest(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        action: str,  # answer, teach_me, skip
        time_spent: int = 0
    ):
        """Update user interest based on their actions"""
        
        # Get or create interest record
        result = await db.execute(
            select(UserInterest).where(
                and_(UserInterest.user_id == user_id, UserInterest.topic_id == topic_id)
            )
        )
        interest = result.scalar_one_or_none()
        
        if not interest:
            interest = UserInterest(
                user_id=user_id,
                topic_id=topic_id,
                interest_score=0.5,
                preference_type="implicit"
            )
            db.add(interest)
        
        # Calculate interest adjustment based on action (BALANCED for meaningful learning)
        if action == "teach_me":
            interest_delta = 0.05  # Small positive - interested but struggling
            interest.preference_type = "explicit"
        elif action == "skip":
            interest_delta = -0.4  # Strong negative - not interested in this topic
            interest.preference_type = "explicit"
        elif action == "answer":
            # Answer signal depends on correctness (should be passed in performance_data)
            # For now, moderate positive signal
            interest_delta = 0.15  # Solid engagement signal
            interest.preference_type = "implicit"
        else:
            interest_delta = 0.0
        
        # Update interest with bounds [0, 1]
        interest.interest_score = max(0.0, min(1.0, interest.interest_score + interest_delta))
        
        # Ensure counters are not None
        if interest.interaction_count is None:
            interest.interaction_count = 0
        if interest.time_spent is None:
            interest.time_spent = 0
            
        interest.interaction_count += 1
        interest.time_spent += time_spent
        interest.updated_at = datetime.utcnow()
        
        # Propagate interest to parent topics (but with less weight)
        await self._propagate_interest_to_parents(db, user_id, topic_id, interest_delta * 0.3)
        
        await db.commit()
        return interest.interest_score
    
    async def _propagate_interest_to_parents(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        interest_delta: float
    ):
        """Propagate interest signals to parent topics"""
        
        # Get parent topic
        result = await db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        
        if topic and topic.parent_id:
            # Update parent interest
            parent_result = await db.execute(
                select(UserInterest).where(
                    and_(UserInterest.user_id == user_id, UserInterest.topic_id == topic.parent_id)
                )
            )
            parent_interest = parent_result.scalar_one_or_none()
            
            if not parent_interest:
                parent_interest = UserInterest(
                    user_id=user_id,
                    topic_id=topic.parent_id,
                    interest_score=0.5,
                    preference_type="inferred"
                )
                db.add(parent_interest)
            
            # Apply smaller delta to parent
            parent_interest.interest_score = max(0.0, min(1.0, 
                parent_interest.interest_score + interest_delta))
            
            # Continue propagating up the tree (with even smaller delta)
            if interest_delta > 0.01:  # Avoid infinite recursion
                await self._propagate_interest_to_parents(
                    db, user_id, topic.parent_id, interest_delta * 0.5
                )
    
    async def check_and_unlock_subtopics(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int
    ) -> List[Dict]:
        """Check if user has achieved proficiency to dynamically generate and unlock subtopics"""
        
        # Get user's progress on this topic
        result = await db.execute(
            select(UserSkillProgress).where(
                and_(UserSkillProgress.user_id == user_id, UserSkillProgress.topic_id == topic_id)
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress or progress.questions_answered < self.min_questions_for_proficiency:
            return []
        
        # Calculate proficiency
        accuracy = progress.correct_answers / progress.questions_answered
        proficiency_level = self._determine_proficiency_level(accuracy, progress.questions_answered)
        
        # Update mastery level
        # Legacy field - don't override current_mastery_level
        # progress.mastery_level = proficiency_level
        
        unlocked_topics = []
        
        # Check if proficiency threshold is met for unlocking or if user has progressed to higher mastery levels
        should_generate_subtopics = (
            # First time reaching proficiency
            (accuracy >= self.PROFICIENCY_THRESHOLDS["beginner"] and not progress.proficiency_threshold_met) or
            # Progressive generation for higher mastery levels with few existing children
            (accuracy >= self.PROFICIENCY_THRESHOLDS["intermediate"] and progress.current_mastery_level in ["competent", "proficient", "expert", "master"])
        )
        
        if should_generate_subtopics:
            progress.proficiency_threshold_met = True
            
            # Get the current topic for generation context
            topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
            current_topic = topic_result.scalar_one_or_none()
            
            if not current_topic:
                return []
            
            # First, try to unlock existing subtopics that match the proficiency level
            existing_subtopics = await self._get_existing_subtopics_for_unlocking(
                db, user_id, topic_id, proficiency_level
            )
            
            # Unlock appropriate existing subtopics
            for subtopic in existing_subtopics:
                # Check if already unlocked
                existing_unlock = await db.execute(
                    select(DynamicTopicUnlock).where(
                        and_(
                            DynamicTopicUnlock.user_id == user_id,
                            DynamicTopicUnlock.unlocked_topic_id == subtopic.id
                        )
                    )
                )
                
                if not existing_unlock.scalar_one_or_none():
                    # Create unlock record
                    unlock = DynamicTopicUnlock(
                        user_id=user_id,
                        parent_topic_id=topic_id,
                        unlocked_topic_id=subtopic.id,
                        unlock_trigger="proficiency"
                    )
                    db.add(unlock)
                    
                    # Create progress record for unlocked topic
                    new_progress = UserSkillProgress(
                        user_id=user_id,
                        topic_id=subtopic.id,
                        is_unlocked=True,
                        unlocked_at=datetime.utcnow()
                    )
                    db.add(new_progress)
                    
                    unlocked_topics.append({
                        "id": subtopic.id,
                        "name": subtopic.name,
                        "description": subtopic.description,
                        "unlock_reason": f"Mastered {proficiency_level} level in parent topic"
                    })
            
            # Only generate new topics if no existing topics were unlocked and we have very few children
            existing_children = await db.execute(
                select(Topic).where(Topic.parent_id == topic_id)
            )
            existing_count = len(existing_children.scalars().all())
            
            # Generate new topics based on different conditions:
            # 1. First time: no existing children
            # 2. Progressive: higher mastery levels with reasonable limits (max 12-15 children to avoid overwhelming)
            max_children_for_progressive = 12  # Reasonable limit for subtopic expansion
            should_generate_new = (
                (existing_count == 0 and len(unlocked_topics) == 0) or  # First time generation
                (progress.current_mastery_level in ["competent", "proficient", "expert"] and 
                 existing_count < max_children_for_progressive and 
                 len(unlocked_topics) == 0)  # Progressive generation for higher mastery
            )
            
            if should_generate_new:
                generation_reason = "no existing children" if existing_count == 0 else f"progressive generation at {progress.current_mastery_level} level"
                print(f"🎯 Generating new subtopics for {current_topic.name} ({generation_reason}, {existing_count} existing)")
                
                # Get user interests for context
                user_interests = await self._get_user_interests_for_generation(db, user_id)
                
                # Dynamically generate new subtopics (no count restriction - AI will determine optimal number)
                generated_subtopics = await self.topic_generator.generate_subtopics(
                    db, current_topic, user_interests, count=None  # Let AI determine how many are needed
                )
                
                # Create the topics in database
                created_topics = await self.topic_generator.create_topics_in_database(
                    db, generated_subtopics, topic_id
                )
                
                # Unlock the newly created topics
                for new_topic in created_topics:
                    # Create unlock record
                    unlock = DynamicTopicUnlock(
                        user_id=user_id,
                        parent_topic_id=topic_id,
                        unlocked_topic_id=new_topic.id,
                        unlock_trigger="proficiency_generated"
                    )
                    db.add(unlock)
                    
                    # Create progress record for unlocked topic
                    new_progress = UserSkillProgress(
                        user_id=user_id,
                        topic_id=new_topic.id,
                        is_unlocked=True,
                        unlocked_at=datetime.utcnow()
                    )
                    db.add(new_progress)
                    
                    unlocked_topics.append({
                        "id": new_topic.id,
                        "name": new_topic.name,
                        "description": new_topic.description,
                        "unlock_reason": f"Generated based on {proficiency_level} proficiency and interests"
                    })
            else:
                print(f"🔓 Skipping generation for {current_topic.name} - already has {existing_count} children, unlocked {len(unlocked_topics)} existing topics")
        
        await db.commit()
        return unlocked_topics
    
    async def check_and_unlock_subtopics_non_blocking(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int
    ) -> List[Dict]:
        """Non-blocking version that only unlocks existing topics, doesn't generate new ones"""
        
        # Get user's progress on this topic
        result = await db.execute(
            select(UserSkillProgress).where(
                and_(UserSkillProgress.user_id == user_id, UserSkillProgress.topic_id == topic_id)
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress or progress.questions_answered < self.min_questions_for_proficiency:
            return []
        
        # Calculate proficiency
        accuracy = progress.correct_answers / progress.questions_answered
        proficiency_level = self._determine_proficiency_level(accuracy, progress.questions_answered)
        
        # Update mastery level
        # Legacy field - don't override current_mastery_level
        # progress.mastery_level = proficiency_level
        
        unlocked_topics = []
        
        # Check if proficiency threshold is met for unlocking or if user has progressed to higher mastery levels
        should_generate_subtopics = (
            # First time reaching proficiency
            (accuracy >= self.PROFICIENCY_THRESHOLDS["beginner"] and not progress.proficiency_threshold_met) or
            # Progressive generation for higher mastery levels with few existing children
            (accuracy >= self.PROFICIENCY_THRESHOLDS["intermediate"] and progress.current_mastery_level in ["competent", "proficient", "expert", "master"])
        )
        
        if should_generate_subtopics:
            progress.proficiency_threshold_met = True
            
            # Get the current topic for generation context
            topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
            current_topic = topic_result.scalar_one_or_none()
            
            if not current_topic:
                return []
            
            # Only try to unlock existing subtopics (no generation)
            existing_subtopics = await self._get_existing_subtopics_for_unlocking(
                db, user_id, topic_id, proficiency_level
            )
            
            # Unlock appropriate existing subtopics
            for subtopic in existing_subtopics:
                # Check if already unlocked
                existing_unlock = await db.execute(
                    select(DynamicTopicUnlock).where(
                        and_(
                            DynamicTopicUnlock.user_id == user_id,
                            DynamicTopicUnlock.unlocked_topic_id == subtopic.id
                        )
                    )
                )
                
                if not existing_unlock.scalar_one_or_none():
                    # Create unlock record
                    unlock = DynamicTopicUnlock(
                        user_id=user_id,
                        parent_topic_id=topic_id,
                        unlocked_topic_id=subtopic.id,
                        unlock_trigger="proficiency"
                    )
                    db.add(unlock)
                    
                    # Create progress record for unlocked topic
                    new_progress = UserSkillProgress(
                        user_id=user_id,
                        topic_id=subtopic.id,
                        is_unlocked=True,
                        unlocked_at=datetime.utcnow()
                    )
                    db.add(new_progress)
                    
                    unlocked_topics.append({
                        "id": subtopic.id,
                        "name": subtopic.name,
                        "description": subtopic.description,
                        "unlock_reason": f"Mastered {proficiency_level} level in parent topic"
                    })
        
        await db.commit()
        return unlocked_topics
    
    async def _get_existing_subtopics_for_unlocking(
        self,
        db: AsyncSession,
        user_id: int,
        parent_topic_id: int,
        proficiency_level: str
    ) -> List[Topic]:
        """Get existing subtopics that should be unlocked based on proficiency"""
        
        # Get all direct children of this topic
        result = await db.execute(
            select(Topic).where(Topic.parent_id == parent_topic_id)
        )
        direct_children = result.scalars().all()
        
        # Filter based on proficiency level
        subtopics_to_unlock = []
        
        for child in direct_children:
            # Check difficulty requirements
            if proficiency_level == "beginner" and child.difficulty_min <= 4:
                subtopics_to_unlock.append(child)
            elif proficiency_level == "intermediate" and child.difficulty_min <= 6:
                subtopics_to_unlock.append(child)
            elif proficiency_level == "advanced" and child.difficulty_min <= 8:
                subtopics_to_unlock.append(child)
            elif proficiency_level == "expert":
                subtopics_to_unlock.append(child)
        
        return subtopics_to_unlock
    
    async def _get_user_interests_for_generation(
        self,
        db: AsyncSession,
        user_id: int
    ) -> List[Dict]:
        """Get user interests formatted for topic generation"""
        
        result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, UserInterest.topic_id == Topic.id)
            .where(UserInterest.user_id == user_id)
            .order_by(UserInterest.interest_score.desc())
        )
        
        interests = []
        for interest, topic in result:
            interests.append({
                "topic_id": topic.id,
                "topic_name": topic.name,
                "interest_score": interest.interest_score,
                "interaction_count": interest.interaction_count
            })
        
        return interests
    
    def _determine_proficiency_level(self, accuracy: float, questions_answered: int) -> str:
        """Determine proficiency level based on accuracy and question count"""
        
        # Require more questions for higher proficiency levels
        if questions_answered < 5:
            return "novice"
        elif accuracy >= 0.95 and questions_answered >= 15:
            return "expert"
        elif accuracy >= 0.85 and questions_answered >= 10:
            return "advanced"
        elif accuracy >= 0.75 and questions_answered >= 8:
            return "intermediate"
        elif accuracy >= 0.6 and questions_answered >= 5:
            return "beginner"
        else:
            return "novice"
    
    async def get_personalized_topic_recommendations(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """Get topic recommendations based on user interests and proficiency"""
        
        # Get user's interests
        interest_result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, UserInterest.topic_id == Topic.id)
            .where(UserInterest.user_id == user_id)
            .order_by(UserInterest.interest_score.desc())
        )
        interests = interest_result.all()
        
        # Get user's unlocked topics
        unlocked_result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        unlocked_topics = {row[1].id: row[0] for row in unlocked_result.all()}
        
        recommendations = []
        
        # 1. High-interest topics that user hasn't mastered
        for interest, topic in interests[:3]:
            if topic.id in unlocked_topics:
                progress = unlocked_topics[topic.id]
                if progress.mastery_level in ["novice", "beginner"]:
                    recommendations.append({
                        "topic": {
                            "id": topic.id,
                            "name": topic.name,
                            "description": topic.description,
                            "difficulty_min": topic.difficulty_min,
                            "difficulty_max": topic.difficulty_max
                        },
                        "reason": "High interest area",
                        "interest_score": interest.interest_score,
                        "priority": "high"
                    })
        
        # 2. Topics related to areas of high proficiency (for exploration)
        high_proficiency_topics = [
            topic_id for topic_id, progress in unlocked_topics.items()
            if progress.mastery_level in ["advanced", "expert"]
        ]
        
        for topic_id in high_proficiency_topics[:2]:
            # Find related topics (siblings or advanced subtopics)
            related_result = await db.execute(
                select(Topic).where(
                    or_(
                        Topic.parent_id == topic_id,  # Subtopics
                        Topic.parent_id == (  # Siblings
                            select(Topic.parent_id).where(Topic.id == topic_id)
                        )
                    )
                ).limit(2)
            )
            related_topics = related_result.scalars().all()
            
            for related_topic in related_topics:
                if related_topic.id not in unlocked_topics:
                    recommendations.append({
                        "topic": {
                            "id": related_topic.id,
                            "name": related_topic.name,
                            "description": related_topic.description,
                            "difficulty_min": related_topic.difficulty_min,
                            "difficulty_max": related_topic.difficulty_max
                        },
                        "reason": "Related to your expertise",
                        "priority": "medium"
                    })
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec["topic"]["id"] not in seen_ids:
                seen_ids.add(rec["topic"]["id"])
                unique_recommendations.append(rec)
        
        return unique_recommendations[:limit]
    
    async def get_user_personalized_ontology(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Get the personalized topic tree for the user"""
        
        # Get all unlocked topics for the user
        unlocked_result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        unlocked_data = unlocked_result.all()
        
        # Get user interests
        interest_result = await db.execute(
            select(UserInterest).where(UserInterest.user_id == user_id)
        )
        interests = {interest.topic_id: interest.interest_score 
                    for interest in interest_result.scalars().all()}
        
        # Build personalized tree
        async def build_personalized_tree(parent_id=None):
            available_topics = [
                (progress, topic) for progress, topic in unlocked_data
                if topic.parent_id == parent_id
            ]
            
            topic_list = []
            for progress, topic in available_topics:
                children = await build_personalized_tree(topic.id)
                
                topic_dict = {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description,
                    "difficulty_min": topic.difficulty_min,
                    "difficulty_max": topic.difficulty_max,
                    "mastery_level": progress.mastery_level,
                    "skill_level": progress.skill_level,
                    "confidence": progress.confidence,
                    "questions_answered": progress.questions_answered,
                    "interest_score": interests.get(topic.id, 0.5),
                    "unlocked_at": progress.unlocked_at.isoformat() if progress.unlocked_at else None,
                    "children": children,
                    "is_locked": False
                }
                topic_list.append(topic_dict)
            
            return topic_list
        
        personalized_tree = await build_personalized_tree()
        return {"topics": personalized_tree}

# Global instance
dynamic_ontology_service = DynamicOntologyService()