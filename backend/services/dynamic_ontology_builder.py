"""
Dynamic Ontology Builder - Creates hierarchical AI knowledge tree adaptively
Builds from general (AI) to specific nodes based on user progress and interest
"""
import asyncio
from typing import Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime

from db.models import Topic, UserSkillProgress, UserInterest, DynamicTopicUnlock
from core.logging_config import logger

class DynamicOntologyBuilder:
    """
    Builds AI ontology tree dynamically based on user progress
    Follows hierarchical structure: AI → Foundations/ML/DL → Specific techniques
    """
    
    def __init__(self):
        # Initialize with only the root AI topic - everything else will be generated dynamically
        self.root_topic = {
            "name": "Artificial Intelligence",
            "level": 0,
            "description": "The study and development of computer systems able to perform tasks requiring human intelligence",
            "prerequisites": [],
            "is_root": True
        }
        
        # Proficiency thresholds for unlocking child topics
        self.UNLOCK_THRESHOLDS = {
            "accuracy": 0.6,      # 60% accuracy required
            "questions": 3,       # At least 3 questions answered
            "interest": 0.4       # 40% interest level
        }
        
        # Import gemini service for dynamic generation
        from services.gemini_service import gemini_service
        self.gemini_service = gemini_service
    
    async def get_next_topics_to_unlock(
        self, 
        db: AsyncSession, 
        user_id: int, 
        limit: int = 3
    ) -> List[Dict]:
        """
        Get the next topics that should be unlocked for the user
        Dynamically generates child topics when prerequisites are met
        """
        
        # Get user's current unlocked topics with their progress
        unlocked_result = await db.execute(
            select(Topic, UserSkillProgress)
            .join(UserSkillProgress, Topic.id == UserSkillProgress.topic_id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        
        unlocked_topics_data = []
        for topic, progress in unlocked_result:
            accuracy = (progress.correct_answers / progress.questions_answered 
                       if progress.questions_answered > 0 else 0)
            
            unlocked_topics_data.append({
                "id": topic.id,
                "name": topic.name,
                "level": self._calculate_topic_level(topic),
                "accuracy": accuracy,
                "questions_answered": progress.questions_answered,
                "mastery_threshold_met": (
                    accuracy >= self.UNLOCK_THRESHOLDS["accuracy"] and
                    progress.questions_answered >= self.UNLOCK_THRESHOLDS["questions"]
                )
            })
        
        # Find topics ready for child generation
        ready_to_unlock = []
        
        for topic_data in unlocked_topics_data:
            if topic_data["mastery_threshold_met"]:
                # Check if this topic already has child topics
                children_result = await db.execute(
                    select(func.count(Topic.id))
                    .where(Topic.parent_id == topic_data["id"])
                )
                child_count = children_result.scalar() or 0
                
                if child_count == 0:
                    # Generate child topics dynamically
                    logger.info(f"Topic '{topic_data['name']}' ready for child generation")
                    child_topics = await self.generate_child_topics(
                        db, 
                        topic_data["name"], 
                        topic_data["level"]
                    )
                    
                    # Convert generated topics to unlock format
                    for child_topic in child_topics:
                        ready_to_unlock.append({
                            "name": child_topic["name"],
                            "description": child_topic["description"],
                            "level": child_topic["level"],
                            "parent_id": topic_data["id"],
                            "parent_name": topic_data["name"],
                            "difficulty_min": child_topic["difficulty_range"][0],
                            "difficulty_max": child_topic["difficulty_range"][1],
                            "is_generated": True
                        })
        
        # If no topics are ready for child generation, check if we need to start with root
        if not ready_to_unlock and not unlocked_topics_data:
            # User has no topics - start with root AI topic
            ready_to_unlock.append({
                "name": self.root_topic["name"],
                "description": self.root_topic["description"],
                "level": self.root_topic["level"],
                "parent_id": None,
                "parent_name": None,
                "difficulty_min": 1,
                "difficulty_max": 4,
                "is_generated": False,
                "is_root": True
            })
        
        # Sort by level (unlock broader topics first) and return limited results
        ready_to_unlock.sort(key=lambda x: (x["level"], x["name"]))
        
        logger.info(f"Found {len(ready_to_unlock)} topics ready to unlock for user {user_id}")
        
        return ready_to_unlock[:limit]
    
    def _calculate_topic_level(self, topic: Topic) -> int:
        """Calculate topic level based on parent hierarchy"""
        if not topic.parent_id:
            return 0  # Root topic
        
        # For now, use a simple heuristic based on difficulty
        # In a more advanced system, this could traverse the parent chain
        if topic.difficulty_min <= 2:
            return 1
        elif topic.difficulty_min <= 4:
            return 2
        elif topic.difficulty_min <= 6:
            return 3
        else:
            return 4
    
    async def unlock_topic_for_user(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_data: Dict
    ) -> Optional[Dict]:
        """
        Unlock a specific topic for the user using dynamic topic data
        Creates the topic in database if it doesn't exist
        """
        
        # Check if topic already exists in database
        existing_result = await db.execute(
            select(Topic).where(Topic.name == topic_data["name"])
        )
        existing_topic = existing_result.scalar_one_or_none()
        
        if not existing_topic:
            # Create new topic
            new_topic = Topic(
                name=topic_data["name"],
                description=topic_data["description"],
                parent_id=topic_data.get("parent_id"),
                difficulty_min=topic_data.get("difficulty_min", 1),
                difficulty_max=topic_data.get("difficulty_max", 5)
            )
            
            db.add(new_topic)
            await db.flush()  # Get the ID
            topic_id = new_topic.id
            
            logger.info(f"Created new topic: {topic_data['name']} (ID: {topic_id})")
        else:
            topic_id = existing_topic.id
        
        # Check if user already has progress for this topic
        existing_progress_result = await db.execute(
            select(UserSkillProgress).where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
        )
        existing_progress = existing_progress_result.scalar_one_or_none()
        
        if not existing_progress:
            # Create user progress entry
            progress = UserSkillProgress(
                user_id=user_id,
                topic_id=topic_id,
                skill_level=0.0,
                confidence=0.0,
                questions_answered=0,
                correct_answers=0,
                mastery_level="novice",
                is_unlocked=True,
                unlocked_at=datetime.utcnow()
            )
            
            db.add(progress)
            
            # Record the unlock event
            unlock_record = DynamicTopicUnlock(
                user_id=user_id,
                parent_topic_id=topic_data.get("parent_id"),
                unlocked_topic_id=topic_id,
                unlock_trigger="progression",
                unlocked_at=datetime.utcnow()
            )
            
            db.add(unlock_record)
            await db.commit()
            
            logger.info(f"Unlocked topic '{topic_data['name']}' for user {user_id}")
        else:
            # Topic already unlocked
            logger.info(f"Topic '{topic_data['name']}' already unlocked for user {user_id}")
        
        return {
            "topic_id": topic_id,
            "name": topic_data["name"],
            "level": topic_data["level"],
            "description": topic_data["description"]
        }
    
    async def check_and_unlock_progressive_topics(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> List[Dict]:
        """
        Check user's progress and unlock next appropriate topics using dynamic generation
        Returns list of newly unlocked topics
        """
        
        # Get topics ready to unlock (dynamically generated)
        ready_topics = await self.get_next_topics_to_unlock(db, user_id, limit=2)
        
        newly_unlocked = []
        
        for topic_data in ready_topics:
            unlocked = await self.unlock_topic_for_user(db, user_id, topic_data)
            if unlocked:
                newly_unlocked.append(unlocked)
        
        return newly_unlocked
    
    
    async def get_learning_path_recommendation(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict:
        """
        Get recommended learning path for the user
        Shows current level and next steps
        """
        
        # Get user's current progress
        progress_result = await db.execute(
            select(UserSkillProgress, Topic)
            .join(Topic, UserSkillProgress.topic_id == Topic.id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        
        current_topics = []
        for progress, topic in progress_result:
            accuracy = (progress.correct_answers / progress.questions_answered 
                       if progress.questions_answered > 0 else 0)
            
            current_topics.append({
                "name": topic.name,
                "accuracy": accuracy,
                "questions_answered": progress.questions_answered,
                "mastery_level": progress.mastery_level
            })
        
        # Get next recommended topics
        next_topics = await self.get_next_topics_to_unlock(db, user_id, limit=3)
        
        return {
            "current_topics": current_topics,
            "next_recommended": next_topics,
            "total_unlocked": len(current_topics)
        }
    
    async def generate_child_topics(
        self, 
        db: AsyncSession,
        parent_topic_name: str, 
        parent_level: int,
        user_interests: List[str] = None
    ) -> List[Dict]:
        """
        Dynamically generate child topics for a given parent topic using AI
        Based on the comprehensive ontology structure example
        """
        
        try:
            # Create a comprehensive prompt based on your excellent example
            prompt = f"""You are an AI education expert. Generate 3-6 child topics for "{parent_topic_name}" at level {parent_level + 1}.

CONTEXT: We're building an infinite, adaptive AI knowledge tree that goes from general to specific. Here's the hierarchical structure we follow:

Level 0: Root (AI)
Level 1: Major domains (Mathematical Foundations, Machine Learning, Deep Learning, NLP, Computer Vision, MLOps, etc.)
Level 2: Sub-domains (Supervised Learning, Unsupervised Learning, Linear Algebra, Probability, etc.)
Level 3: Specific techniques (Regression, Classification, Clustering, CNN, RNN, etc.)
Level 4+: Algorithms and implementations (Linear Regression, SVD, Adam, BERT, etc.)

EXAMPLE HIERARCHICAL STRUCTURE (use as reference):
{{
  "ai": {{
    "name": "Artificial Intelligence",
    "children": [
      {{
        "name": "Mathematical Foundations",
        "children": [
          {{
            "name": "Linear Algebra",
            "children": ["Vectors", "Matrices", "Eigen-Decomposition", "SVD"]
          }},
          {{
            "name": "Probability & Statistics", 
            "children": ["Probability Distributions", "Bayes Rule", "Hypothesis Testing"]
          }},
          {{
            "name": "Optimization",
            "children": ["Convex Optimization", "Gradient Descent Family"]
          }}
        ]
      }},
      {{
        "name": "Machine Learning",
        "children": [
          {{
            "name": "Supervised Learning",
            "children": ["Regression", "Classification", "Model Evaluation"]
          }},
          {{
            "name": "Unsupervised Learning", 
            "children": ["Clustering", "Dimensionality Reduction", "Generative Models"]
          }},
          {{
            "name": "Reinforcement Learning",
            "children": ["Value-Based Methods", "Policy-Based Methods", "Actor-Critic"]
          }}
        ]
      }},
      {{
        "name": "Deep Learning",
        "children": ["Frameworks", "Architectures", "Training Paradigms"]
      }},
      {{
        "name": "Natural Language Processing",
        "children": ["Language Models", "Core Tasks", "Embeddings"]
      }},
      {{
        "name": "Computer Vision", 
        "children": ["Vision Tasks", "Vision Models"]
      }}
    ]
  }}
}}

PARENT TOPIC: {parent_topic_name}
CURRENT LEVEL: {parent_level}
TARGET LEVEL: {parent_level + 1}

REQUIREMENTS:
1. Generate 3-6 educationally appropriate child topics
2. Ensure proper hierarchical progression (don't skip levels)
3. Make topics comprehensive but focused
4. Include both breadth and depth appropriate for the level
5. Consider real-world applications and current AI trends
6. Ensure each topic can have its own meaningful questions

RESPONSE FORMAT (JSON):
{{
  "child_topics": [
    {{
      "name": "Topic Name",
      "description": "Clear, educational description of what this topic covers",
      "level": {parent_level + 1},
      "key_concepts": ["concept1", "concept2", "concept3"],
      "difficulty_range": [1, 10]
    }}
  ]
}}

Generate child topics that maintain educational progression and allow for infinite expansion."""

            # Generate using Gemini
            logger.info(f"Generating child topics for '{parent_topic_name}' at level {parent_level}")
            
            import asyncio
            response = await asyncio.wait_for(
                self.gemini_service.generate_content(prompt),
                timeout=10.0  # 10 second timeout for ontology generation
            )
            
            if not response:
                logger.error(f"Empty response from Gemini for child topics of '{parent_topic_name}'")
                return []
            
            # Parse JSON response
            import json
            import re
            
            # Clean response
            json_content = response.strip()
            if json_content.startswith('```json'):
                json_content = re.sub(r'^```json\s*', '', json_content)
                json_content = re.sub(r'\s*```$', '', json_content)
            elif json_content.startswith('```'):
                json_content = re.sub(r'^```\s*', '', json_content)
                json_content = re.sub(r'\s*```$', '', json_content)
            
            try:
                data = json.loads(json_content)
                child_topics = data.get('child_topics', [])
                
                logger.info(f"Generated {len(child_topics)} child topics for '{parent_topic_name}'")
                return child_topics
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for child topics of '{parent_topic_name}': {e}")
                logger.error(f"Response was: {response}")
                return []
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout generating child topics for '{parent_topic_name}'")
            return []
        except Exception as e:
            logger.error(f"Error generating child topics for '{parent_topic_name}': {e}")
            return []

# Global instance
dynamic_ontology_builder = DynamicOntologyBuilder()