#!/usr/bin/env python3
"""
Create initial questions for the AI root topic
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic, Question

async def create_initial_questions():
    """Create some initial questions for the AI root topic"""
    
    async with AsyncSessionLocal() as session:
        # Get the AI root topic
        result = await session.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = result.scalar_one_or_none()
        
        if not ai_topic:
            print("❌ AI topic not found!")
            return
        
        print(f"📚 Creating initial questions for: {ai_topic.name} (ID: {ai_topic.id})")
        
        # Create 3 initial questions of varying difficulty
        questions = [
            {
                "content": "What is Artificial Intelligence (AI)?",
                "options": [
                    "A computer system that can perform tasks requiring human intelligence",
                    "A type of computer hardware",
                    "A programming language",
                    "A database management system"
                ],
                "correct_answer": "A computer system that can perform tasks requiring human intelligence",
                "explanation": "The correct answer is 'A computer system that can perform tasks requiring human intelligence'. AI refers to the simulation of human intelligence in machines that are programmed to think and learn like humans.",
                "difficulty": 2
            },
            {
                "content": "Which of the following is a key component of machine learning?",
                "options": [
                    "Training data and algorithms",
                    "Only computer processors",
                    "Just programming languages",
                    "Only user interfaces"
                ],
                "correct_answer": "Training data and algorithms",
                "explanation": "The correct answer is 'Training data and algorithms'. Machine learning requires data to learn from and algorithms to process that data and make predictions or decisions.",
                "difficulty": 4
            },
            {
                "content": "What is the main challenge in developing ethical AI systems?",
                "options": [
                    "Balancing automation with human oversight and fairness",
                    "Making computers run faster",
                    "Reducing memory usage",
                    "Creating prettier user interfaces"
                ],
                "correct_answer": "Balancing automation with human oversight and fairness",
                "explanation": "The correct answer is 'Balancing automation with human oversight and fairness'. Ethical AI development involves ensuring systems are fair, transparent, accountable, and respect human values while providing useful automation.",
                "difficulty": 7
            }
        ]
        
        for i, q_data in enumerate(questions, 1):
            question = Question(
                topic_id=ai_topic.id,
                content=q_data["content"],
                question_type="multiple_choice",
                options=q_data["options"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                difficulty=q_data["difficulty"]
            )
            session.add(question)
            print(f"✅ Created question {i}: {q_data['content'][:50]}... (difficulty {q_data['difficulty']})")
        
        await session.commit()
        print(f"\n🎉 Created {len(questions)} initial questions for AI topic!")
        print("🚀 System now has seed questions to start learning!")

if __name__ == "__main__":
    asyncio.run(create_initial_questions())