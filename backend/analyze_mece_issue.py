#!/usr/bin/env python3
"""
Analyze and fix MECE validation issues preventing subtopic generation
"""
import asyncio
import sys
sys.path.append('/Users/acar/projects/relevia/backend')

from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic, UserSkillProgress
from services.dynamic_topic_generator import DynamicTopicGenerator

async def analyze_mece_issue():
    """Analyze why MECE validation is failing"""
    
    async with AsyncSessionLocal() as db:
        # Get Machine Learning topic which has no children
        result = await db.execute(
            select(Topic).where(Topic.name == "Machine Learning")
        )
        ml_topic = result.scalar_one_or_none()
        
        if not ml_topic:
            print("Machine Learning topic not found!")
            return
        
        print(f"Found topic: {ml_topic.name} (ID: {ml_topic.id})")
        print(f"Description: {ml_topic.description}")
        print(f"Difficulty: {ml_topic.difficulty_min}-{ml_topic.difficulty_max}")
        
        # Check for existing children
        children_result = await db.execute(
            select(Topic).where(Topic.parent_id == ml_topic.id)
        )
        children = children_result.scalars().all()
        print(f"\nExisting children: {len(children)}")
        for child in children:
            print(f"  - {child.name}")
        
        # Test the generator directly
        generator = DynamicTopicGenerator()
        
        # Create a test prompt to see what AI generates
        prompt = generator._create_generation_prompt(ml_topic, [], 0.5, None)
        print(f"\n{'='*60}")
        print("PROMPT BEING SENT TO AI:")
        print(prompt)
        print(f"{'='*60}\n")
        
        # Try to generate subtopics
        print("Attempting to generate subtopics...")
        subtopics = await generator.generate_subtopics(db, ml_topic, [], None)
        
        if subtopics:
            print(f"\n✅ Successfully generated {len(subtopics)} subtopics:")
            for st in subtopics:
                print(f"  - {st['name']}: {st['description']}")
        else:
            print("\n❌ Failed to generate subtopics")
            
            # Let's try with a modified validator
            print("\nTesting with relaxed MECE validation...")
            
            # Generate without MECE validation to see what we get
            try:
                from services.gemini_service import GeminiService
                gemini = GeminiService()
                response = await gemini.generate_content(prompt)
                print("\nRaw AI Response:")
                print(response[:500] + "..." if len(response) > 500 else response)
                
                # Parse the response
                parsed = generator._parse_subtopics_response(response, ml_topic)
                print(f"\nParsed {len(parsed)} subtopics:")
                for st in parsed:
                    print(f"  - {st['name']}")
                
                # Check MECE validation
                print("\nMECE Validation Result:")
                is_valid = generator._validate_mece_principles(parsed, ml_topic)
                print(f"Valid: {is_valid}")
                
            except Exception as e:
                print(f"Error during manual generation: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_mece_issue())