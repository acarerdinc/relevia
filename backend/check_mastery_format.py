#!/usr/bin/env python3
import asyncio
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import UserSkillProgress

async def check_mastery_format():
    async with AsyncSessionLocal() as db:
        # Get progress records with mastery data
        result = await db.execute(
            select(UserSkillProgress).where(UserSkillProgress.mastery_questions_answered.isnot(None))
        )
        records = result.scalars().all()
        
        print(f"Found {len(records)} progress records with mastery data")
        
        for record in records[:5]:  # Show first 5
            print(f"\nUser {record.user_id}, Topic {record.topic_id}:")
            print(f"  Current mastery level: {record.current_mastery_level}")
            print(f"  Mastery questions format: {type(record.mastery_questions_answered)}")
            print(f"  Data: {record.mastery_questions_answered}")
            
            # Check format of each level
            if record.mastery_questions_answered:
                for level, data in record.mastery_questions_answered.items():
                    print(f"    {level}: {type(data)} = {data}")

if __name__ == "__main__":
    asyncio.run(check_mastery_format())