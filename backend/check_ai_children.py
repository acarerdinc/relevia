#!/usr/bin/env python3
"""
Check if AI topic has any children in the database
"""
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic

async def check_ai_children():
    async with AsyncSessionLocal() as db:
        # Get AI topic
        ai_result = await db.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = ai_result.scalar_one_or_none()
        
        if not ai_topic:
            print("❌ AI topic not found!")
            return
            
        print(f"✅ Found AI topic: ID={ai_topic.id}")
        
        # Get children
        children_result = await db.execute(
            select(Topic).where(Topic.parent_id == ai_topic.id)
        )
        children = children_result.scalars().all()
        
        print(f"\n📊 Children count: {len(children)}")
        
        if children:
            print("\n📋 Children topics:")
            for child in children:
                print(f"  - {child.name} (ID: {child.id})")
        else:
            print("\n❌ No children found!")
            
        # Check if any of the expected topics exist anywhere
        print("\n🔍 Checking for expected subtopics anywhere in database:")
        expected_names = [
            'Knowledge Representation and Reasoning', 
            'Machine Learning', 
            'Natural Language Processing', 
            'Computer Vision', 
            'Robotics'
        ]
        
        for name in expected_names:
            result = await db.execute(
                select(Topic).where(Topic.name == name)
            )
            topic = result.scalar_one_or_none()
            if topic:
                print(f"  ✅ Found '{name}' - Parent ID: {topic.parent_id}")
            else:
                print(f"  ❌ '{name}' not found")

if __name__ == "__main__":
    asyncio.run(check_ai_children())