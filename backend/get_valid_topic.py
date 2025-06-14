#!/usr/bin/env python3
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import Topic

async def get_valid_topic():
    async with AsyncSessionLocal() as db:
        # Get first available topic
        result = await db.execute(select(Topic).limit(1))
        topic = result.scalar_one_or_none()
        
        if topic:
            print(f"First available topic: ID={topic.id}, Name='{topic.name}'")
            return topic.id
        else:
            print("No topics found!")
            return None

if __name__ == "__main__":
    topic_id = asyncio.run(get_valid_topic())