"""
Adaptive Quiz Service - Unified service that integrates exploration/exploitation with adaptive learning
"""
import asyncio
import math
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime, timedelta
from core.logging_config import logger, performance_logger

from db.models import (
    Topic, QuizSession, Question, QuizQuestion, UserSkillProgress,
    UserInterest, DynamicTopicUnlock
)
from services.adaptive_question_selector import adaptive_question_selector
from services.adaptive_interest_tracker import adaptive_interest_tracker
from services.dynamic_ontology_service import dynamic_ontology_service
from services.gemini_service import gemini_service
import asyncio


class AdaptiveQuizService:
    """
    Unified service that provides intelligent learning experience through:
    - Multi-armed bandit question selection
    - Cross-topic interest tracking
    - Dynamic ontology expansion
    - Engagement optimization
    """
    
    def __init__(self):
        self.session_timeout_minutes = 30
        # No max questions - infinite learning!
        
        # Prefetch cache: {session_id: prefetched_question_data}
        self.prefetch_cache = {}
        self.prefetch_tasks = {}  # Track ongoing prefetch tasks
        
        # Question pool cache: {topic_id: [question_data, ...]}
        self.question_pools = {}
        self.pool_generation_tasks = {}  # Track ongoing pool generation
        self.min_pool_size = 3  # Minimum questions to keep per topic pool
        
    async def start_adaptive_session(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict:
        """
        Start an adaptive learning session (no topic selection required)
        The system intelligently selects the best topic/question based on user profile
        """
        
        # Create a general adaptive session
        session = QuizSession(
            user_id=user_id,
            topic_id=None,  # No specific topic - adaptive across all topics
            started_at=datetime.utcnow(),
            total_questions=0,
            correct_answers=0,
            session_type="adaptive"
        )
        
        db.add(session)
        await db.commit()
        
        # Get user's learning context
        learning_context = await self._get_user_learning_context(db, user_id)
        
        return {
            "session_id": session.id,
            "session_type": "adaptive",
            "learning_context": learning_context,
            "message": "Adaptive learning session started! We'll find the perfect questions for you."
        }
    
    async def get_next_adaptive_question(
        self, 
        db: AsyncSession, 
        session_id: int
    ) -> Optional[Dict]:
        """
        Get the next question using adaptive exploration/exploitation strategy
        Uses prefetched questions when available for instant loading
        """
        import time
        start_time = time.time()
        
        # Get session
        session_result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            return {"error": "Session not found"}
        
        # Check if we have a prefetched question ready
        if session_id in self.prefetch_cache:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Using prefetched question for session {session_id} ({elapsed_ms:.1f}ms)")
            prefetched_data = self.prefetch_cache.pop(session_id)
            
            # Start prefetching the next question in background
            asyncio.create_task(self._prefetch_next_question(session.user_id, session_id))
            
            return prefetched_data
        
        # No prefetched question available, generate normally
        logger.info(f"No prefetched question, generating for session {session_id}")
        question_data = await self._generate_question_for_session(db, session)
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Question generation completed in {elapsed_ms:.1f}ms for session {session_id}")
        
        # Log slow generation
        if elapsed_ms > 2000:
            perf_logger = logger.getChild("performance")
            perf_logger.warning(f"SLOW QUESTION: Generation took {elapsed_ms:.1f}ms for session {session_id}")
        
        if question_data:
            # Start prefetching the next question in background
            asyncio.create_task(self._prefetch_next_question(session.user_id, session_id))
        
        return question_data
    
    async def submit_adaptive_answer(
        self, 
        db: AsyncSession, 
        quiz_question_id: int,
        user_answer: str = None,
        time_spent: int = 0,
        action: str = "answer"  # answer, teach_me, skip
    ) -> Dict:
        """
        Process answer with full adaptive learning pipeline
        """
        
        # Get quiz question with all related data
        result = await db.execute(
            select(QuizQuestion, Question, QuizSession, Topic)
            .join(Question, QuizQuestion.question_id == Question.id)
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .join(Topic, Question.topic_id == Topic.id)
            .where(QuizQuestion.id == quiz_question_id)
        )
        
        row = result.first()
        if not row:
            return {"error": "Quiz question not found"}
        
        quiz_question, question, session, topic = row
        
        # Process the answer
        is_correct = None
        feedback_message = ""
        
        if action == "answer" and user_answer:
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            if is_correct:
                feedback_message = f"Excellent! {question.explanation}"
            else:
                feedback_message = f"Not quite. {question.explanation} Your answer was '{user_answer}', but understanding this concept is what matters most!"
        elif action == "teach_me":
            is_correct = None
            feedback_message = f"Great choice to learn more! {question.explanation} Taking time to understand concepts deeply is a sign of effective learning."
        elif action == "skip":
            is_correct = None
            feedback_message = "No problem! Let's explore something different. Every learner has their own path and pace."
        
        # Update quiz question record
        quiz_question.user_answer = user_answer
        quiz_question.is_correct = is_correct
        quiz_question.answered_at = datetime.utcnow()
        quiz_question.time_spent = time_spent
        quiz_question.user_action = action
        
        # Calculate engagement signal
        engagement_signal = self._calculate_engagement_signal(
            action, is_correct, time_spent, question.difficulty
        )
        quiz_question.interest_signal = engagement_signal
        
        # Update session stats (for all actions)
        if session.total_questions is None:
            session.total_questions = 0
        if session.correct_answers is None:
            session.correct_answers = 0
            
        session.total_questions += 1
        if is_correct:
            session.correct_answers += 1
        
        # Update user progress for answers
        learning_progress = 0.0
        if action == "answer" and is_correct is not None:
            learning_progress = await self._update_adaptive_user_progress(
                db, session.user_id, topic.id, is_correct, question.difficulty
            )
        
        # Track comprehensive interest signals across topic tree
        interest_update = await adaptive_interest_tracker.track_engagement_signals(
            db=db,
            user_id=session.user_id,
            topic_id=topic.id,
            action=action,
            performance_data={
                "accuracy": (session.correct_answers / session.total_questions) if session.total_questions > 0 else 0,
                "time_spent": time_spent,
                "difficulty": question.difficulty,
                "topic_name": topic.name,
                "is_correct": is_correct
            },
            context={
                "session_id": session.id,
                "question_difficulty": question.difficulty
            }
        )
        
        # Update topic rewards for bandit algorithm
        await adaptive_question_selector.update_topic_rewards(
            db, session.user_id, topic.id, engagement_signal, learning_progress
        )
        
        # Check for dynamic topic generation and unlocking
        unlocked_topics = []
        new_interests = []
        
        if action == "answer" and is_correct is not None:
            # Check for topic unlocks
            unlocked_topics = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, session.user_id, topic.id
            )
        
        # Get newly discovered interests
        if interest_update and interest_update.get("new_interests_discovered"):
            new_interests = interest_update["new_interests_discovered"]
        
        await db.commit()
        
        # Start prefetching next question in background while user reads feedback
        logger.info(f"Starting prefetch after answer submission for session {session.id}")
        asyncio.create_task(self._prefetch_next_question(session.user_id, session.id))
        
        # Build comprehensive response
        response = {
            "action": action,
            "correct": is_correct,
            "correct_answer": question.correct_answer if action != "skip" else None,
            "explanation": feedback_message,
            "session_progress": {
                "total_questions": session.total_questions,
                "correct_answers": session.correct_answers,
                "accuracy": session.correct_answers / session.total_questions if session.total_questions > 0 else 0
            },
            "learning_insights": {
                "engagement_level": engagement_signal,
                "learning_progress": learning_progress,
                "topic_mastery": await self._get_topic_mastery_level(db, session.user_id, topic.id)
            }
        }
        
        # Add discovery notifications
        if unlocked_topics:
            response["unlocked_topics"] = unlocked_topics
            response["discovery_message"] = f"🎉 You've unlocked {len(unlocked_topics)} new areas to explore!"
        
        if new_interests:
            response["emerging_interests"] = new_interests
            response["interest_message"] = f"💡 We discovered you might be interested in {len(new_interests)} new topics!"
        
        return response
    
    async def _generate_question_for_session(self, db: AsyncSession, session: QuizSession) -> Optional[Dict]:
        """Generate a question for the session with pool optimization"""
        
        # Use adaptive question selector to find the best question
        question_data = await adaptive_question_selector.select_next_question(
            db, session.user_id, session.id
        )
        
        # If we got a question, ensure its topic's pool is maintained
        if question_data and "topic_id" in question_data:
            await self._ensure_question_pool(db, question_data["topic_id"], session.user_id)
        
        if not question_data:
            return {"error": "No suitable questions found", "suggestion": "explore_new_topics"}
        
        # Handle fallback questions that need to be saved to database first
        if question_data.get('is_fallback', False) and 'question_id' not in question_data:
            # Create the fallback question in the database
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
            await db.flush()  # Get the ID without committing
            
            # Add the question_id to the data
            question_data['question_id'] = new_question.id
            logger.info(f"Created fallback question in database with ID {new_question.id}")
        
        # Create quiz question link
        quiz_question = QuizQuestion(
            quiz_session_id=session.id,
            question_id=question_data["question_id"]
        )
        
        db.add(quiz_question)
        await db.commit()
        
        # Get current topic progress for visual feedback
        topic_progress = await self._get_current_topic_progress(db, session.user_id, question_data["topic_id"])
        
        # Add metadata for adaptive learning
        enhanced_question_data = {
            **question_data,
            "quiz_question_id": quiz_question.id,
            "session_progress": {
                "questions_answered": session.total_questions or 0,
                "session_accuracy": (session.correct_answers / session.total_questions) if session.total_questions > 0 else 0
            },
            "topic_progress": topic_progress,
            "adaptive_metadata": {
                "selection_strategy": question_data.get("selection_strategy", "unknown"),
                "topic_confidence": question_data.get("topic_ucb_score", 0),
                "user_interest": question_data.get("topic_interest_score", 0.5)
            }
        }
        
        return enhanced_question_data
    
    async def _prefetch_next_question(self, user_id: int, session_id: int):
        """Prefetch the next question in background with its own database session"""
        
        from db.database import AsyncSessionLocal
        
        try:
            print(f"🔄 Starting prefetch for session {session_id}")
            
            # Avoid duplicate prefetch tasks
            if session_id in self.prefetch_tasks:
                return
            
            # Mark that we're prefetching for this session
            self.prefetch_tasks[session_id] = True
            
            # Create a new database session for this background task
            async with AsyncSessionLocal() as db:
                # Get session
                session_result = await db.execute(
                    select(QuizSession).where(QuizSession.id == session_id)
                )
                session = session_result.scalar_one_or_none()
                
                if not session:
                    return
                
                # Generate the next question
                question_data = await self._generate_question_for_session(db, session)
                
                if question_data and "error" not in question_data:
                    # Store in prefetch cache
                    self.prefetch_cache[session_id] = question_data
                    logger.info(f"✅ Prefetched question ready for session {session_id}")
                else:
                    logger.warning(f"❌ Failed to prefetch question for session {session_id}")
                    # Don't cache failed attempts - let the main flow handle it
                
        except Exception as e:
            error_logger = logger.getChild("errors")
            error_logger.error(f"Prefetch error for session {session_id}: {str(e)}")
        finally:
            # Remove from active prefetch tasks
            self.prefetch_tasks.pop(session_id, None)
    
    def cleanup_session_cache(self, session_id: int):
        """Clean up cache for completed sessions"""
        self.prefetch_cache.pop(session_id, None)
        self.prefetch_tasks.pop(session_id, None)
        print(f"🧹 Cleaned up cache for session {session_id}")
    
    async def _ensure_question_pool(self, db: AsyncSession, topic_id: int, user_id: int):
        """Ensure a topic has enough questions in its pool, generate if needed"""
        
        # Check if pool has enough questions
        current_pool = self.question_pools.get(topic_id, [])
        
        if len(current_pool) >= self.min_pool_size:
            return  # Pool is healthy
        
        # Avoid duplicate generation tasks
        if topic_id in self.pool_generation_tasks:
            return
        
        print(f"🔄 Question pool for topic {topic_id} needs refilling ({len(current_pool)}/{self.min_pool_size})")
        
        # Start background generation task
        asyncio.create_task(self._refill_question_pool(topic_id, user_id))
    
    async def _refill_question_pool(self, topic_id: int, user_id: int):
        """Background task to refill a topic's question pool"""
        
        from db.database import AsyncSessionLocal
        
        try:
            # Mark that we're generating for this topic
            self.pool_generation_tasks[topic_id] = True
            
            async with AsyncSessionLocal() as db:
                # Get topic info
                topic_result = await db.execute(
                    select(Topic).where(Topic.id == topic_id)
                )
                topic = topic_result.scalar_one_or_none()
                
                if not topic:
                    return
                
                # Generate questions until pool is full
                questions_needed = self.min_pool_size - len(self.question_pools.get(topic_id, []))
                generated_count = 0
                
                for i in range(questions_needed):
                    topic_dict = {
                        'id': topic.id,
                        'name': topic.name,
                        'description': topic.description,
                        'skill_level': 0.5  # Default skill level for pool generation
                    }
                    
                    # Generate question using the selector's method
                    from services.adaptive_question_selector import adaptive_question_selector
                    generated_question = await adaptive_question_selector._generate_question_for_topic(
                        db, user_id, topic_dict
                    )
                    
                    if generated_question:
                        # Add to pool
                        if topic_id not in self.question_pools:
                            self.question_pools[topic_id] = []
                        
                        self.question_pools[topic_id].append(generated_question)
                        generated_count += 1
                        print(f"✅ Added question to pool for topic {topic.name} ({generated_count}/{questions_needed})")
                    else:
                        print(f"❌ Failed to generate question for topic {topic.name}")
                
                print(f"🎉 Question pool refill complete for topic {topic.name}: {generated_count} questions added")
                
        except Exception as e:
            print(f"❌ Pool generation error for topic {topic_id}: {str(e)}")
        finally:
            # Remove task marker
            if topic_id in self.pool_generation_tasks:
                del self.pool_generation_tasks[topic_id]
    
    def get_pooled_question(self, topic_id: int) -> Optional[Dict]:
        """Get a question from the topic's pool if available"""
        
        pool = self.question_pools.get(topic_id, [])
        
        if pool:
            # Pop question from pool (FIFO)
            question = pool.pop(0)
            print(f"🎯 Using pooled question for topic {topic_id} ({len(pool)} remaining in pool)")
            return question
        
        return None
    
    async def get_learning_dashboard(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict:
        """
        Get comprehensive learning dashboard for simplified UI
        """
        
        # Get current learning state
        learning_context = await self._get_user_learning_context(db, user_id)
        
        # Get interest insights
        interest_insights = await adaptive_interest_tracker.get_interest_insights(db, user_id)
        
        # Get exploration stats
        exploration_stats = await adaptive_question_selector.get_exploration_stats(db, user_id)
        
        # Get recent achievements
        recent_unlocks = await self._get_recent_achievements(db, user_id)
        
        # Get personalized recommendations
        recommendations = await self._get_learning_recommendations(db, user_id)
        
        return {
            "learning_state": learning_context,
            "interests": interest_insights,
            "exploration": exploration_stats,
            "recent_achievements": recent_unlocks,
            "recommendations": recommendations,
            "next_action": {
                "type": "continue_learning",
                "description": "Continue your adaptive learning journey",
                "confidence": learning_context.get("readiness_score", 0.8)
            }
        }
    
    async def _get_user_learning_context(self, db: AsyncSession, user_id: int) -> Dict:
        """Get user's current learning context and readiness"""
        
        # Get recent activity
        recent_sessions_result = await db.execute(
            select(QuizSession)
            .where(QuizSession.user_id == user_id)
            .order_by(QuizSession.started_at.desc())
            .limit(5)
        )
        recent_sessions = recent_sessions_result.scalars().all()
        
        # Calculate learning momentum
        if recent_sessions:
            total_questions = sum(s.total_questions or 0 for s in recent_sessions)
            total_correct = sum(s.correct_answers or 0 for s in recent_sessions)
            recent_accuracy = total_correct / total_questions if total_questions > 0 else 0
            
            # Calculate streak and momentum
            learning_momentum = min(1.0, len(recent_sessions) / 5)  # More sessions = higher momentum
        else:
            recent_accuracy = 0
            learning_momentum = 0
        
        # Get last active topic (most recent)
        last_topic_result = await db.execute(
            select(Topic)
            .join(Question, Topic.id == Question.topic_id)
            .join(QuizQuestion, Question.id == QuizQuestion.question_id)
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .where(QuizSession.user_id == user_id)
            .order_by(QuizQuestion.answered_at.desc())
            .limit(1)
        )
        last_topic = last_topic_result.scalar_one_or_none()
        
        # If no recent activity, check highest interest topic
        if not last_topic:
            current_interests_result = await db.execute(
                select(UserInterest, Topic)
                .join(Topic, UserInterest.topic_id == Topic.id)
                .where(UserInterest.user_id == user_id)
                .order_by(UserInterest.interest_score.desc())
                .limit(1)
            )
            current_focus = current_interests_result.first()
            focus_area = current_focus[1].name if current_focus else "Exploring AI Fundamentals"
        else:
            focus_area = f"Continuing: {last_topic.name}"
        
        # Calculate readiness score
        readiness_score = (
            0.4 * recent_accuracy +
            0.3 * learning_momentum +
            0.3 * (1.0 if last_topic else 0.5)
        )
        
        return {
            "focus_area": focus_area,
            "recent_accuracy": recent_accuracy,
            "learning_momentum": learning_momentum,
            "readiness_score": readiness_score,
            "sessions_completed": len(recent_sessions)
        }
    
    def _calculate_engagement_signal(
        self, 
        action: str, 
        is_correct: Optional[bool], 
        time_spent: int, 
        difficulty: int
    ) -> float:
        """Calculate engagement signal for adaptive learning"""
        
        if action == "teach_me":
            return 0.8  # High engagement
        elif action == "skip":
            return -0.3  # Low engagement
        elif action == "answer":
            base_signal = 0.1  # Basic engagement for answering
            
            # Bonus for correct answers
            if is_correct:
                base_signal += 0.2
            
            # Time-based adjustment (sweet spot around 15-25 seconds)
            if 10 <= time_spent <= 30:
                base_signal += 0.1
            elif time_spent > 45:
                base_signal += 0.05  # Thoughtful consideration
            elif time_spent < 5:
                base_signal -= 0.05  # Too quick
            
            # Difficulty bonus
            if difficulty > 7 and is_correct:
                base_signal += 0.15  # Handling hard questions well
            
            return min(1.0, max(-1.0, base_signal))
        
        return 0.0
    
    async def _update_adaptive_user_progress(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        is_correct: bool, 
        question_difficulty: int
    ) -> float:
        """Update user progress and return learning progress signal"""
        
        # Get or create progress
        result = await db.execute(
            select(UserSkillProgress)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
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
                is_unlocked=True,
                unlocked_at=datetime.utcnow()
            )
            db.add(progress)
        
        # Store previous skill level for progress calculation
        previous_skill = progress.skill_level or 0.5
        
        # Update stats
        if progress.questions_answered is None:
            progress.questions_answered = 0
        if progress.correct_answers is None:
            progress.correct_answers = 0
            
        progress.questions_answered += 1
        if is_correct:
            progress.correct_answers += 1
        
        # Adaptive skill level update
        accuracy = progress.correct_answers / progress.questions_answered
        difficulty_factor = question_difficulty / 10.0
        
        if is_correct:
            skill_increase = 0.1 * difficulty_factor * (1 - progress.skill_level)  # Diminishing returns
            progress.skill_level = min(1.0, progress.skill_level + skill_increase)
        else:
            skill_decrease = 0.05 * (1 - difficulty_factor) * progress.skill_level
            progress.skill_level = max(0.0, progress.skill_level - skill_decrease)
        
        # Update confidence and mastery
        progress.confidence = min(accuracy * 0.8, progress.skill_level)
        progress.last_seen = datetime.utcnow()
        
        # Update mastery level
        if accuracy >= 0.9 and progress.questions_answered >= 10:
            progress.mastery_level = "expert"
        elif accuracy >= 0.75 and progress.questions_answered >= 8:
            progress.mastery_level = "advanced"
        elif accuracy >= 0.6 and progress.questions_answered >= 5:
            progress.mastery_level = "intermediate"
        elif progress.questions_answered >= 3:
            progress.mastery_level = "beginner"
        else:
            progress.mastery_level = "novice"
        
        # Calculate learning progress (how much they improved)
        learning_progress = max(0.0, progress.skill_level - previous_skill)
        
        return learning_progress
    
    async def _get_topic_mastery_level(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> Dict:
        """Get detailed mastery information for a topic"""
        
        result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
        )
        
        row = result.first()
        if not row:
            return {"level": "novice", "progress": 0.0}
        
        progress, topic = row
        
        return {
            "level": progress.mastery_level or "novice",
            "skill_score": progress.skill_level or 0.0,
            "confidence": progress.confidence or 0.0,
            "questions_answered": progress.questions_answered or 0,
            "accuracy": (progress.correct_answers / progress.questions_answered) if progress.questions_answered > 0 else 0,
            "topic_name": topic.name
        }
    
    async def _get_recent_achievements(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Get recent learning achievements and unlocks"""
        
        # Get recent topic unlocks
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        unlocks_result = await db.execute(
            select(DynamicTopicUnlock, Topic)
            .join(Topic, DynamicTopicUnlock.unlocked_topic_id == Topic.id)
            .where(
                and_(
                    DynamicTopicUnlock.user_id == user_id,
                    DynamicTopicUnlock.unlocked_at >= week_ago
                )
            )
            .order_by(DynamicTopicUnlock.unlocked_at.desc())
        )
        
        achievements = []
        for unlock, topic in unlocks_result:
            achievements.append({
                "type": "topic_unlock",
                "title": f"New Area Unlocked: {topic.name}",
                "description": topic.description,
                "timestamp": unlock.unlocked_at,
                "trigger": unlock.unlock_trigger
            })
        
        return achievements[:5]  # Recent 5
    
    async def _get_learning_recommendations(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Get personalized learning recommendations"""
        
        # Get recommendations from dynamic ontology service
        recommendations = await dynamic_ontology_service.get_personalized_topic_recommendations(
            db, user_id, limit=3
        )
        
        # Enhance with adaptive insights
        enhanced_recommendations = []
        for rec in recommendations:
            enhanced_recommendations.append({
                **rec,
                "adaptive_score": rec.get("interest_score", 0.5) * 0.6 + rec.get("priority_score", 0.5) * 0.4,
                "learning_time_estimate": self._estimate_learning_time(rec["topic"]["difficulty_max"])
            })
        
        return enhanced_recommendations
    
    async def _get_current_topic_progress(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> Dict:
        """Get current progress for the topic including thresholds"""
        
        # Get user skill progress
        skill_result = await db.execute(
            select(UserSkillProgress)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
        )
        skill_progress = skill_result.scalar_one_or_none()
        
        # Get user interest
        interest_result = await db.execute(
            select(UserInterest)
            .where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.topic_id == topic_id
                )
            )
        )
        interest = interest_result.scalar_one_or_none()
        
        # Get topic info
        topic_result = await db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = topic_result.scalar_one_or_none()
        
        # Calculate current progress
        questions_answered = skill_progress.questions_answered if skill_progress else 0
        correct_answers = skill_progress.correct_answers if skill_progress else 0
        accuracy = correct_answers / questions_answered if questions_answered > 0 else 0
        
        # Import thresholds from dynamic ontology service
        from services.dynamic_ontology_service import DynamicOntologyService
        thresholds = DynamicOntologyService.PROFICIENCY_THRESHOLDS
        min_questions = 3  # From dynamic ontology service
        
        # Calculate progress toward unlock
        proficiency_progress = min(100, (accuracy / thresholds["beginner"]) * 100)
        questions_progress = min(100, (questions_answered / min_questions) * 100)
        
        # Overall unlock progress (need both criteria)
        unlock_progress = min(proficiency_progress, questions_progress)
        
        # Interest score
        interest_score = interest.interest_score if interest else 0.5
        interest_progress = interest_score * 100
        
        # Check if ready to unlock (fixed interest threshold)
        meets_unlock_criteria = (
            accuracy >= thresholds["beginner"] and 
            questions_answered >= min_questions and
            interest_score >= 0.4  # Lowered from 0.5 to 0.4 (medium interest)
        )
        
        # Check if this topic already has subtopics (already unlocked)
        subtopics_result = await db.execute(
            select(Topic).where(Topic.parent_id == topic_id)
        )
        existing_subtopics = subtopics_result.scalars().all()
        has_unlocked_subtopics = len(existing_subtopics) > 0
        
        # Determine unlock status
        if has_unlocked_subtopics:
            ready_to_unlock = False
            unlock_status = "Topics already unlocked - exploring subtopics"
        else:
            ready_to_unlock = meets_unlock_criteria
            unlock_status = "Ready to unlock!" if ready_to_unlock else f"{math.floor(unlock_progress)}% progress"
        
        return {
            "topic_name": topic.name if topic else "Unknown Topic",
            "proficiency": {
                "current_accuracy": accuracy,
                "required_accuracy": thresholds["beginner"],
                "progress_percent": proficiency_progress,
                "questions_answered": questions_answered,
                "min_questions_required": min_questions,
                "questions_progress_percent": questions_progress
            },
            "interest": {
                "current_score": interest_score,
                "progress_percent": interest_progress,
                "level": self._get_interest_level(interest_score)
            },
            "unlock": {
                "ready": ready_to_unlock,
                "overall_progress_percent": unlock_progress,
                "status": unlock_status,
                "has_subtopics": has_unlocked_subtopics,
                "next_threshold": self._get_next_threshold(accuracy, thresholds)
            }
        }
    
    def _get_interest_level(self, score: float) -> str:
        """Convert interest score to readable level"""
        if score >= 0.7:
            return "High"
        elif score >= 0.4:
            return "Medium"
        elif score >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def _get_next_threshold(self, current_accuracy: float, thresholds: Dict) -> Dict:
        """Get next proficiency threshold to aim for"""
        for level, threshold in thresholds.items():
            if current_accuracy < threshold:
                return {"level": level, "accuracy": threshold}
        return {"level": "expert", "accuracy": thresholds["expert"]}
    
    def _estimate_learning_time(self, difficulty: int) -> str:
        """Estimate learning time based on difficulty"""
        if difficulty <= 3:
            return "15-20 minutes"
        elif difficulty <= 6:
            return "25-35 minutes"
        elif difficulty <= 8:
            return "40-60 minutes"
        else:
            return "1-2 hours"


# Global instance
adaptive_quiz_service = AdaptiveQuizService()