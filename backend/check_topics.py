#!/usr/bin/env python3
import asyncio
from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import Topic

async def check_topics():
    async with AsyncSessionLocal() as db:
        # Count topics
        count_result = await db.execute(select(func.count(Topic.id)))
        topic_count = count_result.scalar()
        print(f"Total topics in database: {topic_count}")
        
        # List first few topics if any exist
        if topic_count > 0:
            topics_result = await db.execute(select(Topic).limit(5))
            topics = topics_result.scalars().all()
            print("\nFirst 5 topics:")
            for topic in topics:
                print(f"  ID: {topic.id}, Name: {topic.name}")
        else:
            print("No topics found in database!")

if __name__ == "__main__":
    asyncio.run(check_topics())