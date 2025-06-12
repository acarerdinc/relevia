"""
Script to seed the database with AI ontology
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import engine, Base
from db.models import Topic, TopicPrerequisite
from data.ai_ontology import AI_ONTOLOGY, PREREQUISITES

async def create_topic_hierarchy(session: AsyncSession, topic_data: dict, parent_id: int = None) -> dict:
    """Recursively create topics and return mapping of names to IDs"""
    topic_map = {}
    
    # Create the topic
    topic = Topic(
        name=topic_data["name"],
        description=topic_data.get("description", ""),
        parent_id=parent_id,
        difficulty_min=topic_data.get("difficulty_min", 1),
        difficulty_max=topic_data.get("difficulty_max", 10)
    )
    session.add(topic)
    await session.flush()  # Get the ID
    
    topic_map[topic_data["name"]] = topic.id
    
    # Create children
    if "children" in topic_data:
        for child in topic_data["children"]:
            child_map = await create_topic_hierarchy(session, child, topic.id)
            topic_map.update(child_map)
    
    return topic_map

async def create_prerequisites(session: AsyncSession, topic_map: dict):
    """Create prerequisite relationships"""
    for topic_name, prereqs in PREREQUISITES.items():
        if topic_name in topic_map:
            topic_id = topic_map[topic_name]
            for prereq_name in prereqs:
                if prereq_name in topic_map:
                    prereq = TopicPrerequisite(
                        topic_id=topic_id,
                        prerequisite_id=topic_map[prereq_name]
                    )
                    session.add(prereq)

async def seed_database():
    """Main seeding function"""
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        # Check if already seeded
        from sqlalchemy import text
        existing = await session.execute(text("SELECT COUNT(*) FROM topics"))
        if existing.scalar() > 0:
            print("Database already seeded!")
            return
        
        # Create topic hierarchy
        print("Creating AI topic hierarchy...")
        topic_map = await create_topic_hierarchy(session, AI_ONTOLOGY)
        
        # Create prerequisites
        print("Creating prerequisite relationships...")
        await create_prerequisites(session, topic_map)
        
        # Commit everything
        await session.commit()
        print(f"Successfully created {len(topic_map)} topics!")

if __name__ == "__main__":
    asyncio.run(seed_database())