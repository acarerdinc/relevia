#!/usr/bin/env python3
"""
Migration script to convert all mastery_questions_answered from old complex format to simplified format
Only tracks correct answers per level (no more total/correct objects)
"""
import asyncio
from sqlalchemy import select, update
from sqlalchemy.orm import attributes
from db.database import AsyncSessionLocal
from db.models import UserSkillProgress

async def migrate_mastery_format():
    async with AsyncSessionLocal() as db:
        print("🔄 Starting mastery format migration...")
        
        # Get all progress records
        result = await db.execute(select(UserSkillProgress))
        records = result.scalars().all()
        
        updated_count = 0
        
        for record in records:
            if not record.mastery_questions_answered:
                # Set default simplified format
                record.mastery_questions_answered = {
                    "novice": 0, 
                    "competent": 0, 
                    "proficient": 0, 
                    "expert": 0, 
                    "master": 0
                }
                attributes.flag_modified(record, "mastery_questions_answered")
                updated_count += 1
                continue
            
            # Check if any level has old format (dict with total/correct)
            needs_migration = False
            for level, data in record.mastery_questions_answered.items():
                if isinstance(data, dict):
                    needs_migration = True
                    break
            
            if needs_migration:
                print(f"  Migrating user {record.user_id}, topic {record.topic_id}")
                old_format = record.mastery_questions_answered
                new_format = {
                    "novice": 0, 
                    "competent": 0, 
                    "proficient": 0, 
                    "expert": 0, 
                    "master": 0
                }
                
                for level, data in old_format.items():
                    if isinstance(data, dict) and "correct" in data:
                        new_format[level] = data["correct"]
                    elif isinstance(data, int):
                        new_format[level] = data
                
                record.mastery_questions_answered = new_format
                attributes.flag_modified(record, "mastery_questions_answered")
                updated_count += 1
        
        await db.commit()
        print(f"✅ Migration complete! Updated {updated_count} records to simplified format")
        print("📊 New format only tracks correct answers per level (integers)")

if __name__ == "__main__":
    asyncio.run(migrate_mastery_format())