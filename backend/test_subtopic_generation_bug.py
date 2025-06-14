#!/usr/bin/env python3
"""
Test script to reproduce the subtopic generation bug when reaching Competent level
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.dynamic_topic_generator import DynamicTopicGenerator
from db.database import AsyncSessionLocal
from db.models import Topic
from sqlalchemy import select


async def test_subtopic_generation():
    """Test subtopic generation for Machine Learning topic"""
    
    generator = DynamicTopicGenerator()
    
    async with AsyncSessionLocal() as db:
        # Get Machine Learning topic
        result = await db.execute(
            select(Topic).where(Topic.name == "Machine Learning")
        )
        ml_topic = result.scalar_one_or_none()
        
        if not ml_topic:
            print("Machine Learning topic not found. Creating it...")
            # Get AI root topic
            ai_result = await db.execute(
                select(Topic).where(Topic.name == "Artificial Intelligence")
            )
            ai_topic = ai_result.scalar_one()
            
            ml_topic = Topic(
                name="Machine Learning",
                description="The study of algorithms that improve through experience",
                parent_id=ai_topic.id,
                difficulty_min=3,
                difficulty_max=8
            )
            db.add(ml_topic)
            await db.commit()
            await db.refresh(ml_topic)
        
        print(f"\nTesting subtopic generation for: {ml_topic.name}")
        print(f"Topic ID: {ml_topic.id}")
        # Count existing children
        children_count_result = await db.execute(
            select(Topic).where(Topic.parent_id == ml_topic.id)
        )
        existing_children = children_count_result.scalars().all()
        print(f"Current children count: {len(existing_children)}")
        
        # Test the generation
        print("\n" + "="*60)
        print("STARTING SUBTOPIC GENERATION TEST")
        print("="*60)
        
        try:
            subtopics = await generator.generate_subtopics(db, ml_topic.id, 1)
            
            if subtopics:
                print(f"\n✅ SUCCESS! Generated {len(subtopics)} subtopics:")
                for i, topic in enumerate(subtopics, 1):
                    print(f"  {i}. {topic.name}")
                    print(f"     Description: {topic.description[:100]}...")
                    print(f"     Difficulty: {topic.difficulty_min}-{topic.difficulty_max}")
            else:
                print("\n❌ FAILED! No subtopics generated")
                print("This reproduces the bug - generation fails on first attempt")
                
        except Exception as e:
            print(f"\n❌ ERROR during generation: {e}")
            import traceback
            traceback.print_exc()
        
        # Check database for any created topics
        print("\n" + "="*60)
        print("CHECKING DATABASE STATE")
        print("="*60)
        
        children_result = await db.execute(
            select(Topic).where(Topic.parent_id == ml_topic.id)
        )
        children = children_result.scalars().all()
        
        print(f"Children topics in database: {len(children)}")
        if children:
            for child in children:
                print(f"  - {child.name}")


async def test_mece_validation():
    """Test the MECE validation logic specifically"""
    generator = DynamicTopicGenerator()
    
    # Create a mock parent topic
    class MockTopic:
        def __init__(self):
            self.name = "Machine Learning"
            self.difficulty_min = 3
            self.difficulty_max = 8
    
    parent = MockTopic()
    
    # Test case that should PASS but currently FAILS
    test_subtopics = [
        {"name": "Mathematical Foundations of Machine Learning"},
        {"name": "Deep Learning Architectures"},
        {"name": "Classical ML Algorithms"},
        {"name": "Model Evaluation and Validation"},
        {"name": "Feature Engineering"},
    ]
    
    print("\n" + "="*60)
    print("TESTING MECE VALIDATION")
    print("="*60)
    
    print("Testing subtopics:")
    for s in test_subtopics:
        print(f"  - {s['name']}")
    
    result = generator._validate_mece_principles(test_subtopics, parent)
    print(f"\nValidation result: {'✅ PASSED' if result else '❌ FAILED'}")
    
    if not result:
        print("\nThis shows the bug: valid subtopics are rejected due to overly strict validation")


async def main():
    """Run all tests"""
    print("Testing Subtopic Generation Bug")
    print("="*60)
    
    # Test the actual generation
    await test_subtopic_generation()
    
    # Test the validation logic
    await test_mece_validation()


if __name__ == "__main__":
    asyncio.run(main())