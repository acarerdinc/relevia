"""
Learning Dashboard Service - Generates comprehensive learning insights and dashboards
"""
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from core.logging_config import logger

from db.models import (
    UserSkillProgress, UserInterest, QuizSession, QuizQuestion, 
    Question, Topic, DynamicTopicUnlock
)


class LearningDashboardService:
    """
    Service for generating learning dashboards and insights
    """
    
    async def get_learning_dashboard(self, db: AsyncSession, user_id: int) -> Dict:
        """
        Generate comprehensive learning dashboard for user
        """
        try:
            # Get user progress across all topics (sequential to avoid DB concurrency issues)
            progress_data = await self._get_user_progress_summary(db, user_id)
            
            # Get learning activity over time
            activity_data = await self._get_learning_activity(db, user_id)
            
            # Get interest insights
            interest_data = await self._get_interest_insights(db, user_id)
            
            # Get recently unlocked topics
            unlocked_topics = await self._get_recent_unlocks(db, user_id)
            
            # Get recommended next steps
            recommendations = await self._get_learning_recommendations(db, user_id)
            
            # Get adaptive insights
            adaptive_insights = await self._get_adaptive_insights(db, user_id)
            
            return {
                "user_id": user_id,
                "generated_at": datetime.now().isoformat(),
                "progress_summary": progress_data,
                "learning_activity": activity_data,
                "interests": interest_data,
                "recent_unlocks": unlocked_topics,
                "recommendations": recommendations,
                "adaptive_insights": adaptive_insights
            }
            
        except Exception as e:
            logger.error(f"Error generating dashboard for user {user_id}: {e}")
            return {
                "error": "Failed to generate dashboard",
                "user_id": user_id,
                "generated_at": datetime.now().isoformat()
            }
    
    async def _get_user_progress_summary(self, db: AsyncSession, user_id: int) -> Dict:
        """Get summary of user progress across all topics"""
        result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, Topic.id == UserSkillProgress.topic_id)
            .where(UserSkillProgress.user_id == user_id)
            .order_by(UserSkillProgress.skill_level.desc())
        )
        
        progress_entries = result.all()
        
        if not progress_entries:
            return {
                "total_topics": 0,
                "average_skill_level": 0.0,
                "mastery_distribution": {},
                "top_topics": []
            }
        
        # Calculate statistics
        skill_levels = [p.UserSkillProgress.skill_level or 0 for p, _ in progress_entries]
        avg_skill = sum(skill_levels) / len(skill_levels)
        
        # Mastery distribution
        mastery_counts = {}
        for progress, _ in progress_entries:
            mastery = progress.mastery_level or "novice"
            mastery_counts[mastery] = mastery_counts.get(mastery, 0) + 1
        
        # Top performing topics
        top_topics = []
        for progress, topic in progress_entries[:5]:
            accuracy = (progress.correct_answers / progress.questions_answered 
                       if progress.questions_answered > 0 else 0)
            top_topics.append({
                "topic_name": topic.name,
                "skill_level": progress.skill_level or 0,
                "confidence": progress.confidence or 0,
                "mastery_level": progress.mastery_level or "novice",
                "accuracy": accuracy,
                "questions_answered": progress.questions_answered or 0
            })
        
        return {
            "total_topics": len(progress_entries),
            "average_skill_level": avg_skill,
            "mastery_distribution": mastery_counts,
            "top_topics": top_topics
        }
    
    async def _get_learning_activity(self, db: AsyncSession, user_id: int) -> Dict:
        """Get learning activity data over time"""
        # Get sessions from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        session_result = await db.execute(
            select(QuizSession)
            .where(
                and_(
                    QuizSession.user_id == user_id,
                    QuizSession.started_at >= thirty_days_ago
                )
            )
            .order_by(QuizSession.started_at.desc())
        )
        
        sessions = session_result.scalars().all()
        
        # Calculate activity metrics
        total_sessions = len(sessions)
        total_questions = sum(s.total_questions or 0 for s in sessions)
        total_correct = sum(s.correct_answers or 0 for s in sessions)
        
        # Recent activity (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_sessions = [s for s in sessions if s.started_at >= seven_days_ago]
        
        return {
            "last_30_days": {
                "total_sessions": total_sessions,
                "total_questions": total_questions,
                "total_correct": total_correct,
                "average_accuracy": total_correct / total_questions if total_questions > 0 else 0
            },
            "last_7_days": {
                "sessions": len(recent_sessions),
                "questions": sum(s.total_questions or 0 for s in recent_sessions),
                "accuracy": (
                    sum(s.correct_answers or 0 for s in recent_sessions) /
                    sum(s.total_questions or 0 for s in recent_sessions)
                    if sum(s.total_questions or 0 for s in recent_sessions) > 0 else 0
                )
            }
        }
    
    async def _get_interest_insights(self, db: AsyncSession, user_id: int) -> Dict:
        """Get user interest insights"""
        result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, Topic.id == UserInterest.topic_id)
            .where(UserInterest.user_id == user_id)
            .order_by(UserInterest.interest_score.desc())
        )
        
        interests = result.all()
        
        if not interests:
            return {"top_interests": [], "emerging_interests": []}
        
        # Top interests
        top_interests = []
        for interest, topic in interests[:5]:
            top_interests.append({
                "topic_name": topic.name,
                "interest_score": interest.interest_score,
                "interaction_count": interest.interaction_count,
                "preference_type": interest.preference_type
            })
        
        # Emerging interests (recently updated with growing scores)
        recent_threshold = datetime.now() - timedelta(days=7)
        emerging = [
            {
                "topic_name": topic.name,
                "interest_score": interest.interest_score,
                "trend": "growing"
            }
            for interest, topic in interests
            if interest.updated_at and interest.updated_at >= recent_threshold
               and interest.interest_score > 0.7
        ]
        
        return {
            "top_interests": top_interests,
            "emerging_interests": emerging[:3]
        }
    
    async def _get_recent_unlocks(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Get recently unlocked topics"""
        recent_threshold = datetime.now() - timedelta(days=7)
        
        result = await db.execute(
            select(DynamicTopicUnlock, Topic)
            .join(Topic, Topic.id == DynamicTopicUnlock.unlocked_topic_id)
            .where(
                and_(
                    DynamicTopicUnlock.user_id == user_id,
                    DynamicTopicUnlock.unlocked_at >= recent_threshold
                )
            )
            .order_by(DynamicTopicUnlock.unlocked_at.desc())
        )
        
        unlocks = result.all()
        
        return [
            {
                "topic_name": topic.name,
                "unlocked_at": unlock.unlocked_at.isoformat(),
                "unlock_trigger": unlock.unlock_trigger
            }
            for unlock, topic in unlocks
        ]
    
    async def _get_learning_recommendations(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Generate learning recommendations"""
        recommendations = []
        
        # Find topics with low progress for improvement suggestions
        result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, Topic.id == UserSkillProgress.topic_id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.skill_level < 3.0
                )
            )
            .order_by(UserSkillProgress.skill_level.asc())
            .limit(3)
        )
        
        low_progress_topics = result.all()
        
        for progress, topic in low_progress_topics:
            recommendations.append({
                "type": "skill_improvement",
                "topic_name": topic.name,
                "current_level": progress.skill_level or 0,
                "suggestion": f"Practice more questions in {topic.name} to build foundational knowledge"
            })
        
        # Find high-interest topics for exploration
        interest_result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, Topic.id == UserInterest.topic_id)
            .where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.interest_score > 0.8
                )
            )
            .order_by(UserInterest.interest_score.desc())
            .limit(2)
        )
        
        high_interest_topics = interest_result.all()
        
        for interest, topic in high_interest_topics:
            recommendations.append({
                "type": "interest_exploration",
                "topic_name": topic.name,
                "interest_score": interest.interest_score,
                "suggestion": f"Explore advanced concepts in {topic.name} - you show high interest!"
            })
        
        return recommendations
    
    async def _get_adaptive_insights(self, db: AsyncSession, user_id: int) -> Dict:
        """Get adaptive learning insights"""
        # Count adaptive sessions
        adaptive_sessions_result = await db.execute(
            select(func.count(QuizSession.id))
            .where(
                and_(
                    QuizSession.user_id == user_id,
                    QuizSession.session_type == "adaptive"
                )
            )
        )
        adaptive_sessions_count = adaptive_sessions_result.scalar() or 0
        
        return {
            "adaptive_sessions_completed": adaptive_sessions_count,
            "learning_style": "adaptive_exploration",  # Could be more sophisticated
            "engagement_level": "high"  # Could calculate based on patterns
        }


# Global instance
learning_dashboard_service = LearningDashboardService()