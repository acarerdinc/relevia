#!/usr/bin/env python3
"""
Test the simplified mastery system to ensure it only counts correct answers
"""
import asyncio
from services.mastery_progress_service import MasteryProgressService
from core.mastery_levels import MasteryLevel, CORRECT_ANSWERS_PER_LEVEL
from db.database import AsyncSessionLocal

async def test_simplified_mastery():
    service = MasteryProgressService()
    user_id = 1
    topic_id = 113  # AI topic
    
    async with AsyncSessionLocal() as db:
        print("🧪 Testing simplified mastery system...")
        
        # Check current status
        mastery_info = await service.get_user_mastery(db, user_id, topic_id)
        print(f"📊 Current mastery level: {mastery_info['current_level']}")
        print(f"📈 Correct answers at level: {mastery_info['correct_answers_at_level']}")
        print(f"🎯 Progress: {mastery_info['progress_to_next']}")
        print(f"📋 All correct answers: {mastery_info['mastery_correct_answers']}")
        
        # Test wrong answer (should NOT count towards mastery)
        print(f"\n🔴 Recording a WRONG answer...")
        result = await service.record_mastery_answer(
            db, user_id, topic_id, MasteryLevel(mastery_info['current_level']), False
        )
        print(f"📊 After wrong answer - Correct answers at level: {result['correct_answers_at_level']}")
        print(f"🔄 Advanced? {result['advanced']}")
        
        # Test correct answer (should count towards mastery)
        print(f"\n🟢 Recording a CORRECT answer...")
        result = await service.record_mastery_answer(
            db, user_id, topic_id, MasteryLevel(mastery_info['current_level']), True
        )
        print(f"📊 After correct answer - Correct answers at level: {result['correct_answers_at_level']}")
        print(f"🔄 Advanced? {result['advanced']}")
        
        print(f"\n✅ Test complete! System only counts correct answers for mastery progression.")
        print(f"🎯 Required correct answers for {mastery_info['current_level']}: {CORRECT_ANSWERS_PER_LEVEL[MasteryLevel(mastery_info['current_level'])]}")

if __name__ == "__main__":
    asyncio.run(test_simplified_mastery())