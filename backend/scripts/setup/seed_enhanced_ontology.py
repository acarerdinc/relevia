"""
Seed the enhanced AI ontology with deeper subtopics
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.database import engine, Base
from db.models import Topic, TopicPrerequisite, UserSkillProgress
from data.enhanced_ai_ontology import ENHANCED_AI_ONTOLOGY, ENHANCED_PREREQUISITES

async def create_topic_hierarchy(session: AsyncSession, topic_data: dict, parent_id: int = None) -> dict:
    """Recursively create topics and return mapping of names to IDs"""
    topic_map = {}
    
    # Check if topic already exists
    result = await session.execute(
        select(Topic).where(Topic.name == topic_data["name"])
    )
    existing_topic = result.scalar_one_or_none()
    
    if existing_topic:
        topic_map[topic_data["name"]] = existing_topic.id
        print(f"⏭️  Topic '{topic_data['name']}' already exists, skipping...")
    else:
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
        print(f"✅ Created topic: {topic_data['name']} (ID: {topic.id})")
    
    # Create children
    if "children" in topic_data:
        for child in topic_data["children"]:
            child_map = await create_topic_hierarchy(session, child, topic_map[topic_data["name"]])
            topic_map.update(child_map)
    
    return topic_map

async def create_prerequisites(session: AsyncSession, topic_map: dict):
    """Create prerequisite relationships"""
    print("\n🔗 Creating prerequisite relationships...")
    
    for topic_name, prereqs in ENHANCED_PREREQUISITES.items():
        if topic_name in topic_map:
            topic_id = topic_map[topic_name]
            for prereq_name in prereqs:
                if prereq_name in topic_map:
                    # Check if prerequisite already exists
                    existing = await session.execute(
                        select(TopicPrerequisite).where(
                            TopicPrerequisite.topic_id == topic_id,
                            TopicPrerequisite.prerequisite_id == topic_map[prereq_name]
                        )
                    )
                    
                    if not existing.scalar_one_or_none():
                        prereq = TopicPrerequisite(
                            topic_id=topic_id,
                            prerequisite_id=topic_map[prereq_name]
                        )
                        session.add(prereq)
                        print(f"   • {topic_name} requires {prereq_name}")

async def initialize_user_progress(session: AsyncSession, topic_map: dict, user_id: int = 1):
    """Initialize progress for basic topics for the default user"""
    print(f"\n👤 Initializing progress for user {user_id}...")
    
    # Unlock foundation topics by default
    foundation_topics = [
        "Foundations of AI", "History of AI", "Types of AI", "AI Ethics and Safety",
        "Machine Learning", "Supervised Learning", "Classification", "Regression"
    ]
    
    for topic_name in foundation_topics:
        if topic_name in topic_map:
            topic_id = topic_map[topic_name]
            
            # Check if progress already exists
            existing = await session.execute(
                select(UserSkillProgress).where(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
            
            if not existing.scalar_one_or_none():
                progress = UserSkillProgress(
                    user_id=user_id,
                    topic_id=topic_id,
                    skill_level=0.5,
                    confidence=0.5,
                    mastery_level="novice",
                    is_unlocked=True,
                    unlocked_at=datetime.utcnow()
                )
                session.add(progress)
                print(f"   • Unlocked: {topic_name}")

async def seed_enhanced_ontology():
    """Main seeding function"""
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSession(engine) as session:
        print("🌳 Seeding Enhanced AI Ontology...")
        print("=" * 50)
        
        # Create topic hierarchy
        print("\n📚 Creating topic hierarchy...")
        topic_map = await create_topic_hierarchy(session, ENHANCED_AI_ONTOLOGY)
        
        # Create prerequisites
        await create_prerequisites(session, topic_map)
        
        # Initialize user progress for default user
        await initialize_user_progress(session, topic_map)
        
        # Commit everything
        await session.commit()
        
        print(f"\n🎉 Enhanced ontology seeding completed!")
        print(f"✅ Total topics: {len(topic_map)}")
        print(f"✅ Prerequisites: {len(ENHANCED_PREREQUISITES)}")
        print(f"✅ Foundation topics unlocked for default user")
        
        # Show topic distribution by difficulty
        topic_count_by_difficulty = {}
        for topic_name, topic_id in topic_map.items():
            result = await session.execute(select(Topic).where(Topic.id == topic_id))
            topic = result.scalar_one()
            max_diff = topic.difficulty_max
            if max_diff <= 3:
                level = "Beginner"
            elif max_diff <= 6:
                level = "Intermediate"
            elif max_diff <= 8:
                level = "Advanced"
            else:
                level = "Expert"
            
            topic_count_by_difficulty[level] = topic_count_by_difficulty.get(level, 0) + 1
        
        print(f"\n📊 Topic distribution:")
        for level, count in topic_count_by_difficulty.items():
            print(f"   • {level}: {count} topics")

if __name__ == "__main__":
    asyncio.run(seed_enhanced_ontology())