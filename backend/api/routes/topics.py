from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import Topic

router = APIRouter()

@router.get("/")
async def get_topics(db: AsyncSession = Depends(get_db)):
    """Get all topics in the ontology with hierarchy"""
    
    # Fetch all topics in a single query to avoid multiple round trips
    result = await db.execute(select(Topic).order_by(Topic.name))
    all_topics = result.scalars().all()
    
    # Build a dictionary for quick lookup
    topics_dict = {topic.id: topic for topic in all_topics}
    
    # Build the tree structure in memory
    def build_tree(parent_id=None):
        children = []
        for topic in all_topics:
            if topic.parent_id == parent_id:
                topic_dict = {
                    "id": topic.id,
                    "name": topic.name,
                    "description": topic.description,
                    "difficulty_min": topic.difficulty_min,
                    "difficulty_max": topic.difficulty_max,
                    "children": build_tree(topic.id)
                }
                children.append(topic_dict)
        return children
    
    topics = build_tree()
    return {"topics": topics}

@router.get("/flat")
async def get_topics_flat(db: AsyncSession = Depends(get_db)):
    """Get all topics as a flat list"""
    result = await db.execute(select(Topic).order_by(Topic.name))
    topics = result.scalars().all()
    
    topic_list = []
    for topic in topics:
        topic_list.append({
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "parent_id": topic.parent_id,
            "difficulty_min": topic.difficulty_min,
            "difficulty_max": topic.difficulty_max
        })
    
    return {"topics": topic_list}

@router.get("/{topic_id}")
async def get_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific topic with its children"""
    result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Get children
    children_result = await db.execute(
        select(Topic).where(Topic.parent_id == topic_id)
    )
    children = children_result.scalars().all()
    
    return {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "parent_id": topic.parent_id,
        "difficulty_min": topic.difficulty_min,
        "difficulty_max": topic.difficulty_max,
        "children": [
            {
                "id": child.id,
                "name": child.name,
                "description": child.description
            } for child in children
        ]
    }