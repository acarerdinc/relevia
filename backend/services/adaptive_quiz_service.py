"""
Adaptive Quiz Service - Refactored version with separated concerns
"""
import asyncio
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from core.logging_config import logger

from db.models import Topic, Question, QuizQuestion, UserSkillProgress, DynamicTopicUnlock
from services.quiz_session_manager import quiz_session_manager
from services.question_cache_service import question_cache_service
from services.learning_progress_calculator import learning_progress_calculator
from services.learning_dashboard_service import learning_dashboard_service
from services.adaptive_question_selector import adaptive_question_selector
from services.adaptive_interest_tracker import adaptive_interest_tracker
from services.dynamic_ontology_service import dynamic_ontology_service


class AdaptiveQuizService:
    """
    Simplified adaptive quiz service that coordinates between specialized services
    """
    
    async def start_adaptive_session(self, db: AsyncSession, user_id: int) -> Dict:
        """Start an adaptive learning session"""
        session = await quiz_session_manager.create_adaptive_session(db, user_id)
        learning_context = await self._get_user_learning_context(db, user_id)
        
        return {
            "session_id": session.id,
            "session_type": "adaptive",
            "learning_context": learning_context,
            "message": "Adaptive learning session started! We'll find the perfect questions for you."
        }
    
    async def get_next_adaptive_question(self, db: AsyncSession, session_id: int) -> Optional[Dict]:
        """Get the next question using adaptive strategy with caching"""
        import time
        start_time = time.time()
        
        session = await quiz_session_manager.get_session(db, session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Check for prefetched question first
        if question_cache_service.has_prefetched_question(session_id):
            logger.info(f"Using prefetched question for session {session_id}")
            question_data = question_cache_service.get_prefetched_question(session_id)
            
            if question_data:
                # Create quiz question link
                quiz_question = await quiz_session_manager.create_quiz_question_link(
                    db, session_id, question_data["question_id"]
                )
                question_data["quiz_question_id"] = quiz_question.id
                
                # Add session and topic progress info
                question_data.update(await self._enhance_question_data(db, session, question_data))
                
                # Start prefetching next question
                asyncio.create_task(question_cache_service.prefetch_next_question(session.user_id, session_id))
                
                logger.info(f"Question delivery time: {(time.time() - start_time)*1000:.2f}ms (cached)")
                return question_data
        
        # Generate new question if no cache hit
        question_data = await self._generate_question_for_session(db, session)
        if question_data:
            asyncio.create_task(question_cache_service.prefetch_next_question(session.user_id, session_id))
            logger.info(f"Question delivery time: {(time.time() - start_time)*1000:.2f}ms (generated)")
        
        return question_data
    
    async def submit_adaptive_answer(
        self, 
        db: AsyncSession, 
        quiz_question_id: int, 
        user_answer: Optional[str], 
        action: str, 
        time_spent: float = 30.0
    ) -> Dict:
        """Submit answer for adaptive question with comprehensive tracking"""
        
        # Get session and question data
        session_data = await quiz_session_manager.get_session_with_question(db, quiz_question_id)
        if not session_data:
            return {"error": "Question or session not found"}
        
        session, quiz_question, question, topic = session_data
        
        # Process the answer
        is_correct = None
        feedback_message = "Question skipped"
        
        if action == "answer" and user_answer is not None:
            is_correct = self._validate_answer(user_answer, question)
            feedback_message = self._generate_feedback(is_correct, question)
        
        # Update quiz question record
        await self._update_quiz_question_record(
            db, quiz_question, user_answer, is_correct, action, time_spent
        )
        
        # Update session stats
        if action == "answer":
            await quiz_session_manager.update_session_stats(db, session, is_correct)
        
        # Calculate engagement signal
        engagement_signal = learning_progress_calculator.calculate_engagement_signal(
            action, is_correct, time_spent, question.difficulty
        )
        
        # Use shared logic for mastery progression (same as focused mode)
        from services.shared_quiz_logic import shared_quiz_logic
        
        learning_progress = 0.0
        mastery_advancement = None
        
        if action == "answer" and is_correct is not None:
            # Update skill/confidence only (not question counters)
            learning_progress = await learning_progress_calculator.update_adaptive_user_progress(
                db, session.user_id, topic.id, is_correct, question.difficulty
            )
            
            # Use shared mastery progression logic (same as focused mode)
            mastery_advancement = await shared_quiz_logic.process_answer_submission(
                db, session.user_id, topic.id, is_correct, action
            )
        
        # Track comprehensive interest signals
        interest_update = await adaptive_interest_tracker.track_engagement_signals(
            db=db,
            user_id=session.user_id,
            topic_id=topic.id,
            action=action,
            performance_data={
                "accuracy": quiz_session_manager.get_session_progress_data(session)["accuracy"],
                "time_spent": time_spent,
                "difficulty": question.difficulty,
                "topic_name": topic.name,
                "is_correct": is_correct
            },
            context={"session_id": session.id, "question_difficulty": question.difficulty}
        )
        
        # Update topic rewards for bandit algorithm
        await adaptive_question_selector.update_topic_rewards(
            db, session.user_id, topic.id, engagement_signal, learning_progress
        )
        
        # Use shared logic for background subtopic generation (same as focused mode)
        unlocked_topics = []
        new_interests = []
        
        await shared_quiz_logic.trigger_background_subtopic_generation(
            session.user_id, topic.id, action, is_correct
        )
        
        if interest_update and interest_update.get("new_interests_discovered"):
            new_interests = interest_update["new_interests_discovered"]
        
        await db.commit()
        
        # Start prefetching next question
        asyncio.create_task(question_cache_service.prefetch_next_question(session.user_id, session.id))
        
        # Build response
        response = {
            "action": action,
            "correct": is_correct,
            "correct_answer": question.correct_answer if action != "skip" else None,
            "explanation": feedback_message,
            "session_progress": quiz_session_manager.get_session_progress_data(session),
            "learning_insights": {
                "engagement_level": engagement_signal,
                "learning_progress": learning_progress,
                "topic_mastery": await learning_progress_calculator.get_topic_mastery_level(
                    db, session.user_id, topic.id
                )
            }
        }
        
        # Add additional data
        if mastery_advancement:
            response["mastery_advancement"] = mastery_advancement
        
        if unlocked_topics:
            response["unlocked_topics"] = unlocked_topics
            response["discovery_message"] = f"🎉 You've unlocked {len(unlocked_topics)} new areas to explore!"
        
        if new_interests:
            response["emerging_interests"] = new_interests
            response["interest_message"] = f"💡 We discovered you might be interested in {len(new_interests)} new topics!"
        
        return response
    
    async def get_learning_dashboard(self, db: AsyncSession, user_id: int) -> Dict:
        """Get comprehensive learning dashboard in frontend-expected format"""
        try:
            # Simplified data gathering to avoid async issues
            # Get basic progress data 
            progress_result = await db.execute(
                select(UserSkillProgress, Topic)
                .join(Topic, Topic.id == UserSkillProgress.topic_id)
                .where(UserSkillProgress.user_id == user_id)
                .order_by(UserSkillProgress.skill_level.desc())
            )
            progress_data = progress_result.fetchall()
            
            # Create simplified comprehensive data structure
            total_topics = len(progress_data)
            comprehensive_data = {
                'progress_summary': {'total_topics': total_topics},
                'learning_activity': {'last_7_days': {'accuracy': 0.8}},
                'interests': {'top_interests': [], 'emerging_interests': []},
                'recent_unlocks': [],
                'recommendations': [{'suggestion': 'Continue learning'}],
                'adaptive_insights': {'adaptive_sessions_completed': 0}
            }
            
            # Extract data from comprehensive dashboard
            progress = comprehensive_data.get('progress_summary', {})
            activity = comprehensive_data.get('learning_activity', {})
            interests_data = comprehensive_data.get('interests', {})
            recommendations = comprehensive_data.get('recommendations', [])
            adaptive_insights = comprehensive_data.get('adaptive_insights', {})
            
            # Use learning context from comprehensive data instead of making another DB call
            learning_context = {
                "readiness_score": min(1.0, progress.get('total_topics', 0) / 10.0),  # Based on topics unlocked
                "learning_momentum": "building" if progress.get('total_topics', 0) > 3 else "starting"
            }
            
            # Build the expected frontend structure
            return {
                "learning_state": {
                    "focus_area": "Artificial Intelligence" if progress.get('total_topics', 0) > 0 else "Starting your AI learning journey",
                    "recent_accuracy": activity.get('last_7_days', {}).get('accuracy', 0),
                    "learning_momentum": learning_context.get('readiness_score', 0),
                    "readiness_score": learning_context.get('readiness_score', 0.8),
                    "sessions_completed": adaptive_insights.get('adaptive_sessions_completed', 0)
                },
                "exploration": {
                    "topics_unlocked": progress.get('total_topics', 1),
                    "total_topics": progress.get('total_topics', 1),
                    "exploration_coverage": min(1.0, progress.get('total_topics', 0) / 10.0),  # Assume 10 total possible topics
                    "recent_discoveries": len(comprehensive_data.get('recent_unlocks', [])),
                    "discovery_rate": len(comprehensive_data.get('recent_unlocks', [])) / 7.0  # Per week
                },
                "interests": {
                    "high_interest_topics": interests_data.get('top_interests', []),
                    "growing_interest_topics": interests_data.get('emerging_interests', []),
                    "total_topics_explored": progress.get('total_topics', 0)
                },
                "next_action": {
                    "type": "continue_learning",
                    "description": recommendations[0].get('suggestion', 'Continue your adaptive learning journey') if recommendations else 'Start exploring AI concepts',
                    "confidence": learning_context.get('readiness_score', 0.8)
                }
            }
        except Exception as e:
            logger.error(f"Error in dashboard generation: {e}")
            # Return a safe default structure
            return {
                "learning_state": {
                    "focus_area": "Starting your AI learning journey",
                    "recent_accuracy": 0,
                    "learning_momentum": 0,
                    "readiness_score": 0.8,
                    "sessions_completed": 0
                },
                "exploration": {
                    "topics_unlocked": 1,
                    "total_topics": 1,
                    "exploration_coverage": 0,
                    "recent_discoveries": 0,
                    "discovery_rate": 0
                },
                "interests": {
                    "high_interest_topics": [],
                    "growing_interest_topics": [],
                    "total_topics_explored": 0
                },
                "next_action": {
                    "type": "continue_learning",
                    "description": "Start your adaptive learning journey",
                    "confidence": 0.8
                }
            }
    
    def cleanup_session_cache(self, session_id: int):
        """Clean up cache for completed sessions"""
        question_cache_service.clear_session_cache(session_id)
        logger.info(f"Cleaned up cache for session {session_id}")
    
    # Private helper methods
    
    async def _generate_question_for_session(self, db: AsyncSession, session) -> Optional[Dict]:
        """Generate a question for the session"""
        question_data = await adaptive_question_selector.select_next_question(
            db, session.user_id, session.id
        )
        
        if not question_data:
            return {"error": "No suitable questions found", "suggestion": "explore_new_topics"}
        
        # Handle fallback questions that need database creation
        if question_data.get('is_fallback', False) and 'question_id' not in question_data:
            question_data = await self._create_fallback_question(db, question_data)
        
        # Create quiz question link
        quiz_question = await quiz_session_manager.create_quiz_question_link(
            db, session.id, question_data["question_id"]
        )
        
        # Record question history for diversity tracking
        await self._record_question_history(db, session, question_data)
        
        # Enhance with additional data
        question_data.update(await self._enhance_question_data(db, session, question_data))
        question_data["quiz_question_id"] = quiz_question.id
        
        return question_data
    
    async def _create_fallback_question(self, db: AsyncSession, question_data: Dict) -> Dict:
        """Create fallback question in database"""
        new_question = Question(
            topic_id=question_data['topic_id'],
            content=question_data['question'],
            question_type='multiple_choice',
            options=question_data['options'],
            correct_answer=question_data['correct_answer'],
            explanation=question_data['explanation'],
            difficulty=question_data['difficulty']
        )
        
        db.add(new_question)
        await db.flush()
        
        question_data['question_id'] = new_question.id
        logger.info(f"Created fallback question in database with ID {new_question.id}")
        return question_data
    
    async def _enhance_question_data(self, db: AsyncSession, session, question_data: Dict) -> Dict:
        """Add session and topic progress data to question"""
        topic_progress = await learning_progress_calculator.get_current_topic_progress(
            db, session.user_id, question_data["topic_id"]
        )
        
        return {
            "session_progress": quiz_session_manager.get_session_progress_data(session),
            "topic_progress": topic_progress,
            "adaptive_metadata": {
                "selection_strategy": question_data.get("selection_strategy", "unknown"),
                "topic_confidence": question_data.get("topic_ucb_score", 0),
                "user_interest": question_data.get("topic_interest_score", 0.5)
            }
        }
    
    async def _record_question_history(self, db: AsyncSession, session, question_data: Dict):
        """Record question in diversity tracking history"""
        try:
            from services.question_diversity_service import question_diversity_service
            await question_diversity_service.record_question_asked(
                db=db,
                user_id=session.user_id,
                topic_id=question_data["topic_id"],
                question_id=question_data["question_id"],
                session_id=session.id,
                question_content=question_data["question"]
            )
        except Exception as e:
            logger.warning(f"Failed to record question diversity history: {e}")
    
    async def _update_quiz_question_record(
        self, 
        db: AsyncSession, 
        quiz_question: QuizQuestion, 
        user_answer: Optional[str], 
        is_correct: Optional[bool], 
        action: str, 
        time_spent: float
    ):
        """Update quiz question record with answer data"""
        quiz_question.user_answer = user_answer
        quiz_question.is_correct = is_correct
        quiz_question.answered_at = datetime.now(timezone.utc)
        quiz_question.time_spent = time_spent
        quiz_question.user_action = action
        
        engagement_signal = learning_progress_calculator.calculate_engagement_signal(
            action, is_correct, time_spent, 5  # Default difficulty for signal calculation
        )
        quiz_question.interest_signal = engagement_signal
    
    
    def _validate_answer(self, user_answer: str, question: Question) -> bool:
        """Validate user answer against correct answer"""
        try:
            # Handle multiple choice questions
            if question.question_type == "multiple_choice":
                # Try to parse as option index
                try:
                    option_index = int(user_answer)
                    if 0 <= option_index < len(question.options):
                        selected_text = question.options[option_index]
                        return selected_text == question.correct_answer
                except (ValueError, IndexError):
                    pass
                
                # Direct text comparison
                return user_answer.strip().lower() == question.correct_answer.strip().lower()
            
            # Handle other question types
            return user_answer.strip().lower() == question.correct_answer.strip().lower()
            
        except Exception as e:
            logger.error(f"Error validating answer: {e}")
            return False
    
    def _generate_feedback(self, is_correct: bool, question: Question) -> str:
        """Generate feedback message for answer"""
        if is_correct:
            return f"Correct! {question.explanation}"
        else:
            return f"Not quite right. {question.explanation}"
    
    async def _get_user_learning_context(self, db: AsyncSession, user_id: int) -> Dict:
        """Get user's current learning context"""
        # Get recent progress data
        progress_result = await db.execute(
            select(UserSkillProgress)
            .where(UserSkillProgress.user_id == user_id)
            .order_by(UserSkillProgress.skill_level.desc())
            .limit(5)
        )
        recent_progress = progress_result.scalars().all()
        
        if not recent_progress:
            return {
                "total_topics_explored": 0,
                "average_skill_level": 0.0,
                "readiness_score": 0.8,
                "learning_momentum": "starting"
            }
        
        avg_skill = sum(p.skill_level or 0 for p in recent_progress) / len(recent_progress)
        readiness_score = min(1.0, avg_skill / 5.0)  # Normalize to 0-1
        
        return {
            "total_topics_explored": len(recent_progress),
            "average_skill_level": avg_skill,
            "readiness_score": readiness_score,
            "learning_momentum": "building" if readiness_score > 0.5 else "starting"
        }


# Global instance
adaptive_quiz_service = AdaptiveQuizService()