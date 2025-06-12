#!/usr/bin/env python3
"""
Quick script to reset user progress for testing
"""
import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import AsyncSessionLocal
from db.models import QuizSession, QuizQuestion, UserSkillProgress, UserInterest
from sqlalchemy import delete, select

async def reset_user_progress(user_id: int = 1):
    """Reset all progress for a specific user"""
    async with AsyncSessionLocal() as db:
        print(f"🧹 Resetting progress for user {user_id}...")
        
        # Delete quiz questions for this user's sessions
        session_ids_result = await db.execute(
            select(QuizSession.id).where(QuizSession.user_id == user_id)
        )
        session_ids = [row[0] for row in session_ids_result.fetchall()]
        
        if session_ids:
            await db.execute(
                delete(QuizQuestion).where(QuizQuestion.quiz_session_id.in_(session_ids))
            )
        
        # Delete quiz sessions
        await db.execute(delete(QuizSession).where(QuizSession.user_id == user_id))
        
        # Reset user progress (keep unlocked status but reset stats)
        from sqlalchemy import update
        await db.execute(
            update(UserSkillProgress)
            .where(UserSkillProgress.user_id == user_id)
            .values(
                questions_answered=0,
                correct_answers=0,
                skill_level=0.0,
                confidence=0.0,
                mastery_level='novice'
            )
        )
        
        # Reset user interests
        await db.execute(
            update(UserInterest)
            .where(UserInterest.user_id == user_id)
            .values(
                interest_score=0.5,
                interaction_count=0,
                time_spent=0
            )
        )
        
        await db.commit()
        print(f"✅ User {user_id} progress reset complete!")
        print("   - All quiz sessions deleted")
        print("   - Skill progress reset to novice")
        print("   - Interest scores reset to neutral")
        print("   - Topics remain unlocked")

if __name__ == "__main__":
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(reset_user_progress(user_id))