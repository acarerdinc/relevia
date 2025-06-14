"""
Quiz Service - Handles adaptive quiz logic and session management
"""
import asyncio
import random
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from db.models import Topic, QuizSession, Question, QuizQuestion, UserSkillProgress
from services.gemini_service import gemini_service
from services.mastery_question_generator import MasteryQuestionGenerator
from services.mastery_progress_service import MasteryProgressService
from services.learning_progress_calculator import learning_progress_calculator
from core.mastery_levels import MasteryLevel
from core.logging_config import logger

class AdaptiveQuizEngine:
    """
    Manages adaptive quiz sessions and difficulty adjustment
    """
    
    def __init__(self):
        self.difficulty_adjustment_factor = 0.2
        self.min_questions_for_adaptation = 2
        self.mastery_generator = MasteryQuestionGenerator()
        self.mastery_progress = MasteryProgressService()
    
    async def start_quiz_session(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int,
        mastery_level: str = None
    ) -> QuizSession:
        """Start a new quiz session for a user"""
        
        # Determine target mastery level
        if mastery_level:
            target_mastery = MasteryLevel(mastery_level)
        else:
            target_mastery = await self.mastery_progress.get_recommended_mastery_level(db, user_id, topic_id)
        
        # Create new quiz session
        quiz_session = QuizSession(
            user_id=user_id,
            topic_id=topic_id,
            started_at=datetime.utcnow(),
            total_questions=0,
            correct_answers=0,
            mastery_level=target_mastery.value
        )
        
        db.add(quiz_session)
        await db.flush()
        return quiz_session
    
    async def get_next_question(
        self, 
        db: AsyncSession, 
        session_id: int
    ) -> Optional[Dict]:
        """
        Get next question for a quiz session, avoiding duplicates
        Uses adaptive algorithm to determine difficulty
        """
        
        # Get quiz session
        result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None
        
        # Get topic info
        topic_result = await db.execute(
            select(Topic).where(Topic.id == session.topic_id)
        )
        topic = topic_result.scalar_one_or_none()
        if not topic:
            return None
        
        # Determine target mastery level and difficulty
        session_mastery = MasteryLevel(session.mastery_level)
        target_difficulty = await self._calculate_target_difficulty(
            db, session.user_id, topic.id, session.id
        )
        
        # Get questions already asked in this session
        asked_questions_result = await db.execute(
            select(QuizQuestion.question_id)
            .where(QuizQuestion.quiz_session_id == session_id)
        )
        asked_question_ids = [row[0] for row in asked_questions_result.fetchall()]
        
        # Try to find an existing unused question that matches our mastery level and difficulty
        existing_question = None
        if asked_question_ids:
            # Look for questions not already asked at the target mastery level
            existing_result = await db.execute(
                select(Question)
                .where(
                    Question.topic_id == topic.id,
                    Question.mastery_level == session_mastery.value,
                    Question.difficulty >= target_difficulty - 1,
                    Question.difficulty <= target_difficulty + 1,
                    ~Question.id.in_(asked_question_ids)  # Not in asked questions
                )
                .limit(1)
            )
        else:
            # No questions asked yet, any suitable question works
            existing_result = await db.execute(
                select(Question)
                .where(
                    Question.topic_id == topic.id,
                    Question.mastery_level == session_mastery.value,
                    Question.difficulty >= target_difficulty - 1,
                    Question.difficulty <= target_difficulty + 1
                )
                .limit(1)
            )
        
        existing_question = existing_result.scalar_one_or_none()
        
        # Use existing question if found, otherwise generate new one
        if existing_question:
            question = existing_question
            print(f"🔄 Reusing existing question: {question.content[:50]}...")
        else:
            # Generate new mastery-specific question
            existing_questions_text = []
            if asked_question_ids:
                existing_result = await db.execute(
                    select(Question.content)
                    .where(Question.id.in_(asked_question_ids))
                )
                existing_questions_text = [row[0] for row in existing_result.fetchall()]
            
            question_data = await self.mastery_generator.generate_mastery_question(
                db, topic, session_mastery, existing_questions_text
            )
            
            # Store new question in database
            question = Question(
                topic_id=topic.id,
                content=question_data["question"],
                question_type="multiple_choice",
                options=question_data["options"],
                correct_answer=question_data["correct_answer"],
                explanation=question_data["explanation"],
                difficulty=question_data["difficulty"],
                mastery_level=session_mastery.value
            )
            
            db.add(question)
            await db.flush()
            print(f"✨ Generated new question: {question.content[:50]}...")
        
        # Create quiz question record (links session to question)
        quiz_question = QuizQuestion(
            quiz_session_id=session.id,
            question_id=question.id
        )
        
        db.add(quiz_question)
        await db.commit()
        
        # Record question in history for diversity tracking
        try:
            from services.question_diversity_service import question_diversity_service
            await question_diversity_service.record_question_asked(
                db=db,
                user_id=session.user_id,
                topic_id=topic.id,
                question_id=question.id,
                session_id=session.id,
                question_content=question.content
            )
            logger.info(f"Recorded question diversity history for question {question.id}")
        except Exception as e:
            logger.warning(f"Failed to record question diversity history: {e}")
            # Don't fail the question generation if history tracking fails
        
        # Get user progress for this topic to include progress information
        user_progress_result = await db.execute(
            select(UserSkillProgress)
            .where(
                UserSkillProgress.user_id == session.user_id,
                UserSkillProgress.topic_id == topic.id
            )
        )
        user_progress = user_progress_result.scalar_one_or_none()
        
        # Calculate session progress
        session_questions = session.total_questions or 0
        session_correct = session.correct_answers or 0
        session_accuracy = (session_correct / session_questions) if session_questions > 0 else 0
        
        # Calculate topic progress
        topic_questions = user_progress.questions_answered if user_progress else 0
        topic_correct = user_progress.correct_answers if user_progress else 0
        topic_accuracy = (topic_correct / topic_questions) if topic_questions > 0 else 0
        
        # DEBUG MODE: Skip shuffling and provide correct answer index for frontend highlighting
        debug_mode = True  # Enabled for fast debugging
        debug_correct_index = None
        
        if debug_mode:
            # Don't shuffle in debug mode - keep original order
            shuffled_options = question.options.copy()
            shuffled_correct = question.correct_answer
            
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
            shuffled_options, shuffled_correct = self._shuffle_question_options(
                question.options, question.correct_answer
            )
        
        # Return question in the same format as adaptive API
        result = {
            "question_id": question.id,
            "quiz_question_id": quiz_question.id,
            "question": question.content,
            "options": shuffled_options,
            "correct_answer": shuffled_correct,  # Include shuffled correct answer for frontend
            "difficulty": question.difficulty,
            "topic_name": topic.name,
            "selection_strategy": "focused",
            "mastery_level": user_progress.current_mastery_level if user_progress else "novice",
            "session_progress": {
                "questions_answered": session_questions,
                "session_accuracy": session_accuracy,
                "questions_remaining": None  # Not applicable for focused learning
            },
            "topic_progress": await learning_progress_calculator.get_current_topic_progress(
                db, session.user_id, topic.id
            )
        }
        
        # Add debug info if in debug mode
        if debug_mode and debug_correct_index is not None:
            result["debug_correct_index"] = debug_correct_index
            
        return result
    
    async def submit_answer(
        self, 
        db: AsyncSession, 
        quiz_question_id: int,
        user_answer: str = None,
        time_spent: int = 0,
        action: str = "answer"  # answer, teach_me, skip
    ) -> Dict:
        """
        Process user's answer and provide feedback
        Updates user progress and session statistics
        """
        
        # Get quiz question with related data
        result = await db.execute(
            select(QuizQuestion, Question, QuizSession)
            .join(Question, QuizQuestion.question_id == Question.id)
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .where(QuizQuestion.id == quiz_question_id)
        )
        
        row = result.first()
        if not row:
            return {"error": "Quiz question not found"}
        
        quiz_question, question, session = row
        
        # Handle different actions
        is_correct = None
        feedback_message = ""
        
        if action == "answer" and user_answer is not None:
            # Handle both index-based and text-based answers
            if isinstance(user_answer, int) or (isinstance(user_answer, str) and user_answer.isdigit()):
                # Index-based answer (0, 1, 2, 3)
                option_index = int(user_answer)
                if 0 <= option_index < len(question.options):
                    selected_option = question.options[option_index]
                    
                    # DEBUG: Strip debug symbol if present
                    if selected_option.startswith("✓ "):
                        selected_option = selected_option[2:]
                    
                    # Handle different answer formats
                    # Case 1: Correct answer is just letter (e.g., "A")
                    if len(question.correct_answer.strip()) == 1 and question.correct_answer.strip().upper() in 'ABCD':
                        # Extract letter from option (e.g., "A) text..." -> "A")
                        option_letter = selected_option.strip()[0].upper() if selected_option.strip() else ''
                        is_correct = option_letter == question.correct_answer.strip().upper()
                    else:
                        # Case 2: Correct answer is full text
                        is_correct = selected_option.strip().lower() == question.correct_answer.strip().lower()
                else:
                    is_correct = False
            else:
                # Text-based answer (legacy)
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            
            if is_correct:
                feedback_message = f"Excellent! {question.explanation}"
            else:
                feedback_message = f"Not quite. {question.explanation}"
        elif action == "teach_me":
            # User wants to learn more about this topic
            is_correct = None  # Don't count as right or wrong
            feedback_message = f"Great choice! Here's what you should know: {question.explanation}"
        elif action == "skip":
            # User wants to skip this question
            is_correct = None  # Don't count as right or wrong
            feedback_message = "Question skipped. You can always come back to this topic later."
        
        # Update quiz question record
        quiz_question.user_answer = str(user_answer) if user_answer is not None else None
        quiz_question.is_correct = is_correct
        quiz_question.answered_at = datetime.utcnow()
        quiz_question.time_spent = time_spent
        quiz_question.user_action = action
        
        # Set interest signal (numeric values)
        if action == "teach_me":
            quiz_question.interest_signal = 0.8  # High interest
        elif action == "skip":
            quiz_question.interest_signal = -0.3  # Low interest (negative)
        else:
            quiz_question.interest_signal = 0.1  # Neutral interest
        
        # Update session statistics (only for actual answers)
        if action == "answer":
            # Ensure counters are not None
            if session.total_questions is None:
                session.total_questions = 0
            if session.correct_answers is None:
                session.correct_answers = 0
                
            session.total_questions += 1
            if is_correct:
                session.correct_answers += 1
        
        # Update mastery progress and get current status
        mastery_advancement = None
        if action == "answer" and is_correct is not None:
            # Only use the mastery system - it handles all progress tracking
            session_mastery = MasteryLevel(session.mastery_level)
            mastery_advancement = await self.mastery_progress.record_mastery_answer(
                db, session.user_id, question.topic_id, session_mastery, is_correct
            )
            
            # Legacy skill update for confidence/skill_level (but not questions_answered)
            await self._update_user_skill_only(
                db, session.user_id, question.topic_id, is_correct, question.difficulty
            )
        else:
            # For non-answer actions, still provide current mastery status
            mastery_advancement = await self.mastery_progress.get_current_mastery_status(
                db, session.user_id, question.topic_id
            )
        
        # Update user interest based on action
        from services.dynamic_ontology_service import dynamic_ontology_service
        await dynamic_ontology_service.update_user_interest(
            db, session.user_id, question.topic_id, action, time_spent
        )
        
        # Check for topic unlocks after interest/proficiency update (true background task)
        unlocked_topics = []
        if action == "answer" and is_correct is not None:
            # Run topic unlocking as true background task - don't wait for it
            async def background_subtopic_generation():
                try:
                    # Create new database session for background task
                    from db.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as bg_db:
                        await dynamic_ontology_service.check_and_unlock_subtopics(
                            bg_db, session.user_id, question.topic_id
                        )
                        print(f"✅ Background subtopic generation completed for user {session.user_id}, topic {question.topic_id}")
                except Exception as e:
                    print(f"⚠️ Background topic unlock failed for user {session.user_id}: {e}")
            
            # Start background task without waiting
            asyncio.create_task(background_subtopic_generation())
        
        await db.commit()
        
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
            "mastery_level": session.mastery_level
        }
        
        # Add mastery advancement information
        if mastery_advancement:
            response["mastery_advancement"] = mastery_advancement
        
        # Add unlock information if any topics were unlocked
        if unlocked_topics:
            response["unlocked_topics"] = unlocked_topics
        
        return response
    
    async def _calculate_target_difficulty(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        session_id: int
    ) -> int:
        """
        Calculate the target difficulty for the next question
        Uses user's historical performance and current session
        """
        
        # Get user's skill progress for this topic
        progress_result = await db.execute(
            select(UserSkillProgress)
            .where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        # Get current session performance
        session_result = await db.execute(
            select(QuizSession).where(QuizSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        
        # Get topic difficulty range
        topic_result = await db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = topic_result.scalar_one_or_none()
        
        if not topic:
            return 5  # Default difficulty
        
        # Base difficulty on skill level or start in middle
        if progress and progress.questions_answered >= self.min_questions_for_adaptation:
            base_difficulty = progress.skill_level * (topic.difficulty_max - topic.difficulty_min) + topic.difficulty_min
        else:
            base_difficulty = (topic.difficulty_min + topic.difficulty_max) / 2
        
        # Adjust based on recent session performance
        if session and session.total_questions > 0:
            accuracy = session.correct_answers / session.total_questions
            if accuracy > 0.8:  # Too easy, increase difficulty
                base_difficulty += 1
            elif accuracy < 0.4:  # Too hard, decrease difficulty
                base_difficulty -= 1
        
        # Clamp to topic's difficulty range
        target_difficulty = max(topic.difficulty_min, min(topic.difficulty_max, int(base_difficulty)))
        
        return target_difficulty
    
    async def _update_user_progress(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        is_correct: bool, 
        question_difficulty: int
    ):
        """Update user's skill progress based on question performance"""
        
        # Get existing progress or create new
        result = await db.execute(
            select(UserSkillProgress)
            .where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
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
                correct_answers=0
            )
            db.add(progress)
        
        # Update statistics (ensure not None)
        if progress.questions_answered is None:
            progress.questions_answered = 0
        if progress.correct_answers is None:
            progress.correct_answers = 0
            
        progress.questions_answered += 1
        if is_correct:
            progress.correct_answers += 1
        
        # Update skill level using Bayesian-like approach
        accuracy = progress.correct_answers / progress.questions_answered
        
        # Adjust skill level based on performance and question difficulty
        difficulty_factor = question_difficulty / 10.0  # Normalize to 0-1
        
        if is_correct:
            # Correct answer increases skill level
            skill_increase = self.difficulty_adjustment_factor * difficulty_factor
            progress.skill_level = min(1.0, progress.skill_level + skill_increase)
        else:
            # Incorrect answer decreases skill level
            skill_decrease = self.difficulty_adjustment_factor * (1 - difficulty_factor)
            progress.skill_level = max(0.0, progress.skill_level - skill_decrease)
        
        # Update confidence based on consistency
        progress.confidence = min(accuracy, progress.skill_level)
        progress.last_seen = datetime.utcnow()
    
    async def _update_user_skill_only(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        is_correct: bool, 
        question_difficulty: int
    ):
        """Update only skill level and confidence, not question counters (handled by mastery system)"""
        
        # Get existing progress
        result = await db.execute(
            select(UserSkillProgress)
            .where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            return  # Mastery system should have created this
        
        # Only update skill-related fields, not counters
        accuracy = progress.correct_answers / progress.questions_answered if progress.questions_answered > 0 else 0
        difficulty_factor = question_difficulty / 10.0  # Normalize to 0-1
        
        if is_correct:
            # Correct answer increases skill level
            skill_increase = self.difficulty_adjustment_factor * difficulty_factor
            progress.skill_level = min(1.0, progress.skill_level + skill_increase)
        else:
            # Incorrect answer decreases skill level
            skill_decrease = self.difficulty_adjustment_factor * (1 - difficulty_factor)
            progress.skill_level = max(0.0, progress.skill_level - skill_decrease)
        
        # Update confidence based on consistency
        progress.confidence = min(accuracy, progress.skill_level)
        progress.last_seen = datetime.utcnow()
    
    def _shuffle_question_options(self, options: List[str], correct_answer: str) -> tuple[List[str], str]:
        """Shuffle question options and return new correct answer"""
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
                return options, correct_answer
        
        # Create a list of indices and shuffle them
        indices = list(range(len(shuffled_options)))
        random.shuffle(indices)
        
        # Reorder options according to shuffled indices
        shuffled_options = [options[i] for i in indices]
        
        # Find where the correct answer ended up after shuffling
        new_correct_index = indices.index(correct_index)
        new_correct_answer = shuffled_options[new_correct_index]
        
        return shuffled_options, new_correct_answer

# Global instance
quiz_engine = AdaptiveQuizEngine()