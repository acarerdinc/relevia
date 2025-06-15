from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from db.database import get_db
from db.models import User, UserSkillProgress, Topic, QuizSession, QuizQuestion, Question
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from services.mastery_progress_service import MasteryProgressService

router = APIRouter()

@router.get("/")
async def get_progress(db: AsyncSession = Depends(get_db)):
    """Get user's learning progress"""
    # TODO: Implement progress tracking
    return {"progress": "Not implemented yet"}

@router.get("/user/{user_id}")
async def get_user_progress(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get comprehensive user progress including ontology tree"""
    
    # First check if user exists, if not create basic progress
    user_check = await db.execute(select(User).where(User.id == user_id))
    user = user_check.scalar_one_or_none()
    if not user:
        # Create a default user for demo purposes
        user = User(id=user_id, email=f"demo{user_id}@example.com", 
                   username=f"demo{user_id}", hashed_password="demo")
        db.add(user)
        await db.commit()
    
    # Get all topics with user progress in a single query
    result = await db.execute(
        select(Topic, UserSkillProgress)
        .join(
            UserSkillProgress,
            and_(
                Topic.id == UserSkillProgress.topic_id,
                UserSkillProgress.user_id == user_id
            ),
            isouter=True
        )
        .order_by(Topic.parent_id.nullsfirst(), Topic.name)
    )
    
    all_topics_with_progress = result.all()
    
    topics_data = []
    total_questions = 0
    total_correct = 0
    topics_unlocked = 0
    
    for topic, progress in all_topics_with_progress:
        
        # Default values for topics without progress
        is_unlocked = False
        mastery_level = "novice"
        current_mastery_level = "novice"
        questions_answered = 0
        correct_answers = 0
        skill_level = 0.0
        confidence = 0.0
        unlocked_at = None
        mastery_questions_answered = {"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}
        
        if progress:
            total_questions += progress.questions_answered or 0
            total_correct += progress.correct_answers or 0
            
            if progress.is_unlocked:
                topics_unlocked += 1
            
            is_unlocked = progress.is_unlocked
            mastery_level = progress.mastery_level or "novice"
            current_mastery_level = progress.current_mastery_level or "novice"
            questions_answered = progress.questions_answered or 0
            correct_answers = progress.correct_answers or 0
            skill_level = progress.skill_level or 0.0
            confidence = progress.confidence or 0.0
            unlocked_at = progress.unlocked_at.isoformat() if progress.unlocked_at else None
            mastery_questions_answered = progress.mastery_questions_answered or {"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}
            
            # Add explicit field for current level's correct answers
            correct_answers_at_current_level = mastery_questions_answered.get(current_mastery_level, 0)
            
            # Add individual fields for each level (for frontend compatibility)
            novice_correct_answers = mastery_questions_answered.get("novice", 0)
            competent_correct_answers = mastery_questions_answered.get("competent", 0)
            proficient_correct_answers = mastery_questions_answered.get("proficient", 0)
            expert_correct_answers = mastery_questions_answered.get("expert", 0)
            master_correct_answers = mastery_questions_answered.get("master", 0)
        else:
            # For root topics (parent_id is None), unlock them by default
            if topic.parent_id is None:
                is_unlocked = True
                topics_unlocked += 1
            
        topics_data.append({
            "id": topic.id,
            "name": topic.name,
            "parent_id": topic.parent_id,
            "description": topic.description,
            "difficulty_min": topic.difficulty_min,
            "difficulty_max": topic.difficulty_max,
            "is_unlocked": is_unlocked,
            "mastery_level": mastery_level,
            "current_mastery_level": current_mastery_level,
            "questions_answered": questions_answered,
            "correct_answers": correct_answers,
            "correct_answers_at_current_level": correct_answers_at_current_level if progress else 0,
            "skill_level": skill_level,
            "confidence": confidence,
            "unlocked_at": unlocked_at,
            "mastery_questions_answered": mastery_questions_answered,
            "mastery_correct_answers": mastery_questions_answered,  # Add alias for frontend compatibility
            "novice_correct_answers": novice_correct_answers if progress else 0,
            "competent_correct_answers": competent_correct_answers if progress else 0,
            "proficient_correct_answers": proficient_correct_answers if progress else 0,
            "expert_correct_answers": expert_correct_answers if progress else 0,
            "master_correct_answers": master_correct_answers if progress else 0
        })
    
    # Calculate overall mastery progress (average mastery level across unlocked topics)
    mastery_weights = {"novice": 0, "competent": 1, "proficient": 2, "expert": 3, "master": 4}
    total_mastery_score = 0
    unlocked_topics_count = 0
    
    for topic_data in topics_data:
        if topic_data["is_unlocked"]:
            unlocked_topics_count += 1
            mastery_level = topic_data["current_mastery_level"]
            total_mastery_score += mastery_weights.get(mastery_level, 0)
    
    overall_mastery_progress = 0
    if unlocked_topics_count > 0:
        overall_mastery_progress = total_mastery_score / (unlocked_topics_count * 4)  # Normalize to 0-1 scale
    
    # Skip expensive streak and velocity calculations for now
    # These can be loaded asynchronously on the frontend if needed
    current_streak = 0
    learning_velocity = 0.0
    
    return {
        "total_topics_unlocked": topics_unlocked,
        "overall_mastery_progress": overall_mastery_progress,
        "total_questions_answered": total_questions,
        "current_streak": current_streak,
        "learning_velocity": learning_velocity,
        "topics": topics_data
    }

def calculate_streak(sessions: List[datetime]) -> int:
    """Calculate consecutive days of learning"""
    if not sessions:
        return 0
    
    streak = 1
    last_date = sessions[0].date()
    
    for session in sessions[1:]:
        session_date = session.date()
        if (last_date - session_date).days == 1:
            streak += 1
            last_date = session_date
        else:
            break
            
    return streak

async def calculate_learning_velocity(db: AsyncSession, user_id: int) -> float:
    """Calculate rate of improvement over last 7 days"""
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # Get accuracy progression over last week
    result = await db.execute(
        select(
            func.date(QuizQuestion.answered_at).label('date'),
            func.avg(func.cast(QuizQuestion.is_correct, func.Float)).label('accuracy')
        )
        .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
        .where(
            and_(
                QuizSession.user_id == user_id,
                QuizQuestion.answered_at >= week_ago
            )
        )
        .group_by(func.date(QuizQuestion.answered_at))
        .order_by(func.date(QuizQuestion.answered_at))
    )
    
    daily_accuracies = result.fetchall()
    
    if len(daily_accuracies) < 2:
        return 0.0
    
    # Calculate trend (simple linear regression slope)
    n = len(daily_accuracies)
    x_sum = sum(range(n))
    y_sum = sum(acc.accuracy for acc in daily_accuracies)
    xy_sum = sum(i * acc.accuracy for i, acc in enumerate(daily_accuracies))
    x2_sum = sum(i * i for i in range(n))
    
    if n * x2_sum - x_sum * x_sum == 0:
        return 0.0
        
    slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
    
    # Normalize to percentage
    return max(-1.0, min(1.0, slope))  # Clamp between -100% and 100%

@router.get("/topic/{topic_id}/details")
async def get_topic_progress_details(topic_id: int, user_id: int = 1, db: AsyncSession = Depends(get_db)):
    """Get detailed progress for a specific topic"""
    
    # Get topic with progress
    result = await db.execute(
        select(Topic, UserSkillProgress)
        .join(UserSkillProgress, 
              and_(
                  Topic.id == UserSkillProgress.topic_id,
                  UserSkillProgress.user_id == user_id
              ),
              isouter=True
        )
        .where(Topic.id == topic_id)
    )
    
    topic, progress = result.first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Get recent questions answered
    recent_questions_result = await db.execute(
        select(QuizQuestion)
        .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
        .where(
            and_(
                QuizSession.user_id == user_id,
                QuizQuestion.question_id.in_(
                    select(Question.id).where(Question.topic_id == topic_id)
                )
            )
        )
        .order_by(QuizQuestion.answered_at.desc())
        .limit(10)
    )
    
    recent_questions = recent_questions_result.scalars().all()
    
    # Get detailed mastery information
    mastery_service = MasteryProgressService()
    mastery_info = None
    if progress:
        mastery_info = await mastery_service.get_user_mastery(db, user_id, topic_id)
    
    # Get child topics
    children_result = await db.execute(
        select(Topic, UserSkillProgress)
        .join(UserSkillProgress,
              and_(
                  Topic.id == UserSkillProgress.topic_id,
                  UserSkillProgress.user_id == user_id
              ),
              isouter=True
        )
        .where(Topic.parent_id == topic_id)
    )
    
    children = []
    for child_topic, child_progress in children_result:
        children.append({
            "id": child_topic.id,
            "name": child_topic.name,
            "is_unlocked": child_progress.is_unlocked if child_progress else False,
            "accuracy": (child_progress.correct_answers / child_progress.questions_answered 
                        if child_progress and child_progress.questions_answered > 0 else 0)
        })
    
    return {
        "topic": {
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "parent_id": topic.parent_id
        },
        "progress": {
            "is_unlocked": progress.is_unlocked if progress else False,
            "questions_answered": progress.questions_answered if progress else 0,
            "correct_answers": progress.correct_answers if progress else 0,
            "accuracy": (progress.correct_answers / progress.questions_answered 
                        if progress and progress.questions_answered > 0 else 0),
            "mastery_level": progress.mastery_level if progress else "not_started",
            "current_mastery_level": progress.current_mastery_level if progress else "novice",
            "skill_level": progress.skill_level if progress else 0,
            "confidence": progress.confidence if progress else 0,
            "mastery_questions_answered": progress.mastery_questions_answered if progress else {"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0},
            "mastery_info": mastery_info
        },
        "recent_activity": [
            {
                "answered_at": q.answered_at.isoformat() if q.answered_at else None,
                "is_correct": q.is_correct,
                "time_taken": q.time_spent
            } for q in recent_questions
        ],
        "children": children
    }