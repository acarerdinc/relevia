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

class AdaptiveQuizEngine:
    """
    Manages adaptive quiz sessions and difficulty adjustment
    """
    
    def __init__(self):
        self.difficulty_adjustment_factor = 0.2
        self.min_questions_for_adaptation = 2
    
    async def start_quiz_session(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> QuizSession:
        """Start a new quiz session for a user"""
        
        # Create new quiz session
        quiz_session = QuizSession(
            user_id=user_id,
            topic_id=topic_id,
            started_at=datetime.utcnow(),
            total_questions=0,
            correct_answers=0
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
        
        # Determine difficulty based on user's performance
        target_difficulty = await self._calculate_target_difficulty(
            db, session.user_id, topic.id, session.id
        )
        
        # Get questions already asked in this session
        asked_questions_result = await db.execute(
            select(QuizQuestion.question_id)
            .where(QuizQuestion.quiz_session_id == session_id)
        )
        asked_question_ids = [row[0] for row in asked_questions_result.fetchall()]
        
        # Try to find an existing unused question that matches our difficulty target
        existing_question = None
        if asked_question_ids:
            # Look for questions not already asked
            existing_result = await db.execute(
                select(Question)
                .where(
                    Question.topic_id == topic.id,
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
            # Generate new question using Gemini
            question_data = await gemini_service.generate_question(
                topic=topic.name,
                difficulty=target_difficulty,
                context={
                    "topic_description": topic.description,
                    "difficulty_range": f"{topic.difficulty_min}-{topic.difficulty_max}",
                    "session_progress": f"{session.correct_answers or 0}/{session.total_questions or 0}",
                    "avoid_duplicates": "Generate a unique question different from previous ones"
                }
            )
            
            # Store new question in database
            question = Question(
                topic_id=topic.id,
                content=question_data["question"],
                question_type="multiple_choice",
                options=question_data["options"],
                correct_answer=question_data["correct_answer"],
                explanation=question_data["explanation"],
                difficulty=target_difficulty
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
        
        # Return question without revealing correct answer
        return {
            "question_id": question.id,
            "quiz_question_id": quiz_question.id,
            "question": question.content,
            "options": question.options,
            "difficulty": question.difficulty,
            "topic": topic.name
        }
    
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
        
        if action == "answer" and user_answer:
            # Normal answer submission
            is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
            feedback_message = question.explanation
        elif action == "teach_me":
            # User wants to learn more about this topic
            is_correct = None  # Don't count as right or wrong
            feedback_message = f"Great choice! Here's what you should know: {question.explanation}"
        elif action == "skip":
            # User wants to skip this question
            is_correct = None  # Don't count as right or wrong
            feedback_message = "Question skipped. You can always come back to this topic later."
        
        # Update quiz question record
        quiz_question.user_answer = user_answer
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
        
        # Update user skill progress (only for actual answers)
        if action == "answer" and is_correct is not None:
            await self._update_user_progress(
                db, session.user_id, question.topic_id, is_correct, question.difficulty
            )
        
        # Update user interest based on action
        from services.dynamic_ontology_service import dynamic_ontology_service
        await dynamic_ontology_service.update_user_interest(
            db, session.user_id, question.topic_id, action, time_spent
        )
        
        # Check for topic unlocks after interest/proficiency update
        unlocked_topics = []
        if action == "answer" and is_correct is not None:
            unlocked_topics = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, session.user_id, question.topic_id
            )
        
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
            }
        }
        
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

# Global instance
quiz_engine = AdaptiveQuizEngine()