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
    
    async def find_optimal_parent_topic(
        self, 
        db: AsyncSession,
        learning_request: str,
        existing_topics: List[Dict]
    ) -> Dict:
        """
        Find the optimal parent topic for a user's learning request
        """
        
        # Use Gemini to interpret the learning request
        interpretation = await self.gemini_service.interpret_learning_request(
            learning_request, 
            existing_topics
        )
        
        logger.info(f"Learning request interpretation: {interpretation}")
        
        return interpretation
    
    async def create_user_requested_topic(
        self,
        db: AsyncSession,
        user_id: int,
        learning_request: str
    ) -> Dict:
        """
        Create a new topic based on user's free text learning request
        """
        
        # Get existing topics for context
        existing_topics_result = await db.execute(
            select(Topic)
        )
        existing_topics = []
        for topic in existing_topics_result.scalars().all():
            existing_topics.append({
                "name": topic.name,
                "description": topic.description,
                "level": self._calculate_topic_level(topic)
            })
        
        # Get AI interpretation of the request
        interpretation = await self.find_optimal_parent_topic(
            db, learning_request, existing_topics
        )
        
        # Check if topic already exists or has strong semantic matches
        if interpretation.get("already_exists"):
            existing_match = interpretation.get("existing_topic_match")
            if existing_match:
                # Find the existing topic and unlock it for the user
                existing_topic_result = await db.execute(
                    select(Topic).where(Topic.name.ilike(f"%{existing_match}%")).limit(1)
                )
                existing_topic = existing_topic_result.scalar_one_or_none()
                
                if existing_topic:
                    # Set high interest and unlock
                    await self._set_user_interest(db, user_id, existing_topic.id, 0.9, "explicit")
                    await self._unlock_topic_for_user(db, user_id, existing_topic.id)
                    await db.commit()
                    
                    return {
                        "success": True,
                        "action": "existing_topic_unlocked",
                        "topic_id": existing_topic.id,
                        "topic_name": existing_topic.name,
                        "message": f"Found existing topic '{existing_topic.name}' and unlocked it for you!",
                        "confidence": interpretation["confidence"],
                        "reasoning": f"This topic already covers what you want to learn: {interpretation.get('reasoning', '')}"
                    }
        
        # Check for semantic matches that user might want instead
        semantic_matches = interpretation.get("semantic_matches", [])
        
        # Enhance semantic matching by also checking common relevant topics
        llm_terms = ["llm", "large language", "language model", "gpt", "bert", "transformer"]
        if any(term in learning_request.lower() for term in llm_terms):
            # For LLM requests, always check these important topics
            important_topics = [
                "Modern AI: Machine Learning Revolution",
                "Introduction to Neural Networks and Deep Learning",
                "Natural Language Processing"
            ]
            for topic in important_topics:
                if topic not in semantic_matches:
                    semantic_matches.append(topic)
        
        if semantic_matches and len(semantic_matches) > 0:
            # Find the best semantic match by checking quality of match
            best_match = None
            best_match_score = 0
            
            for match_name in semantic_matches[:5]:  # Check top 5 matches
                match_result = await db.execute(
                    select(Topic).where(Topic.name.ilike(f"%{match_name}%")).limit(1)
                )
                potential_match = match_result.scalar_one_or_none()
                if potential_match:
                    # Score the match based on semantic relevance for LLM-related requests
                    score = self._calculate_semantic_match_score(
                        learning_request.lower(), 
                        potential_match.name.lower(),
                        interpretation.get("parsed_topic", "").lower()
                    )
                    
                    if score > best_match_score:
                        best_match = potential_match
                        best_match_score = score
            
            if best_match:
                # Unlock the semantically similar topic
                await self._set_user_interest(db, user_id, best_match.id, 0.8, "semantic_match")
                await self._unlock_topic_for_user(db, user_id, best_match.id)
                await db.commit()
                
                return {
                    "success": True,
                    "action": "semantic_match_unlocked",
                    "topic_id": best_match.id,
                    "topic_name": best_match.name,
                    "message": f"Found '{best_match.name}' which covers similar concepts!",
                    "confidence": interpretation["confidence"],
                    "reasoning": f"This existing topic is semantically similar to your request. You can also create a more specific topic if needed."
                }
        
        # Find parent topic
        parent_topic = None
        if interpretation.get("suggested_parent"):
            parent_result = await db.execute(
                select(Topic).where(Topic.name == interpretation["suggested_parent"])
            )
            parent_topic = parent_result.scalar_one_or_none()
        
        # Create new topic
        new_topic = Topic(
            name=interpretation["parsed_topic"],
            description=interpretation["description"],
            parent_id=parent_topic.id if parent_topic else None,
            difficulty_min=max(1, interpretation["difficulty_level"] - 2),
            difficulty_max=min(10, interpretation["difficulty_level"] + 2)
        )
        
        db.add(new_topic)
        await db.flush()  # Get the ID
        
        # Set high user interest (explicit request)
        await self._set_user_interest(db, user_id, new_topic.id, 0.9, "explicit")
        
        # Create user progress and unlock immediately
        progress = UserSkillProgress(
            user_id=user_id,
            topic_id=new_topic.id,
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
            parent_topic_id=parent_topic.id if parent_topic else None,
            unlocked_topic_id=new_topic.id,
            unlock_trigger="user_request",
            unlocked_at=datetime.utcnow()
        )
        
        db.add(unlock_record)
        await db.commit()
        
        logger.info(f"Created user-requested topic '{new_topic.name}' for user {user_id}")
        
        return {
            "success": True,
            "action": "new_topic_created",
            "topic_id": new_topic.id,
            "topic_name": new_topic.name,
            "parent_name": parent_topic.name if parent_topic else "Root",
            "confidence": interpretation["confidence"],
            "reasoning": interpretation.get("reasoning", ""),
            "message": f"Created new topic '{new_topic.name}' and unlocked it for you!"
        }
    
    async def _set_user_interest(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        interest_score: float,
        preference_type: str = "explicit"
    ):
        """Set or update user interest for a topic"""
        
        # Check if interest already exists
        existing_interest_result = await db.execute(
            select(UserInterest).where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.topic_id == topic_id
                )
            )
        )
        existing_interest = existing_interest_result.scalar_one_or_none()
        
        if existing_interest:
            # Update existing interest
            existing_interest.interest_score = max(existing_interest.interest_score, interest_score)
            existing_interest.preference_type = preference_type
            existing_interest.updated_at = datetime.utcnow()
        else:
            # Create new interest record
            interest = UserInterest(
                user_id=user_id,
                topic_id=topic_id,
                interest_score=interest_score,
                interaction_count=1,
                time_spent=0,
                preference_type=preference_type
            )
            db.add(interest)
    
    async def _unlock_topic_for_user(self, db: AsyncSession, user_id: int, topic_id: int):
        """Unlock an existing topic for a user"""
        
        # Check if progress already exists
        existing_progress_result = await db.execute(
            select(UserSkillProgress).where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == topic_id
                )
            )
        )
        existing_progress = existing_progress_result.scalar_one_or_none()
        
        if existing_progress:
            # Update to unlock
            existing_progress.is_unlocked = True
            if not existing_progress.unlocked_at:
                existing_progress.unlocked_at = datetime.utcnow()
        else:
            # Create new progress record
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
    
    def _calculate_semantic_match_score(self, request: str, topic_name: str, parsed_topic: str) -> float:
        """
        Calculate a semantic match score to prioritize better matches
        Higher score = better match
        """
        score = 0.0
        
        # LLM-specific scoring rules
        llm_terms = ["llm", "large language", "language model", "gpt", "bert", "transformer"]
        ml_general_terms = ["machine learning", "ai", "artificial intelligence", "modern ai", "revolution"]
        neural_general_terms = ["neural network", "deep learning", "introduction"]
        neural_specific_terms = ["tensorflow", "keras", "cnn", "build", "backpropagation", "algorithm"]
        
        request_has_llm = any(term in request for term in llm_terms)
        topic_has_ml_general = any(term in topic_name for term in ml_general_terms)
        topic_has_neural_general = any(term in topic_name for term in neural_general_terms)
        topic_has_neural_specific = any(term in topic_name for term in neural_specific_terms)
        
        if request_has_llm:
            # For LLM requests, prefer general ML/AI topics over specific neural network building
            if topic_has_ml_general and not topic_has_neural_specific:
                score += 15.0  # Highest preference for general ML/AI topics
            elif topic_has_neural_general and not topic_has_neural_specific:
                score += 8.0   # Good preference for general neural network topics
            elif topic_has_neural_specific:
                score += 1.0   # Very low preference for specific neural network building/algorithm topics
            else:
                score += 5.0   # Medium preference for other topics
        
        # Boost score for topics that mention key concepts from parsed topic
        parsed_words = parsed_topic.split()
        for word in parsed_words:
            if len(word) > 3 and word in topic_name:  # Avoid matching small words
                score += 3.0
        
        # Boost score for broader, more foundational topics over specific implementations
        if "introduction" in topic_name or "fundamentals" in topic_name or "modern" in topic_name:
            score += 2.0
        elif "building" in topic_name or "implementation" in topic_name or "algorithm" in topic_name:
            score -= 3.0  # Strong penalty for very specific implementation topics
        
        # Special penalties for clearly inappropriate topics
        if "backpropagation" in topic_name.lower() and request_has_llm:
            score -= 5.0  # Strong penalty for backpropagation when asking about LLMs
        
        return score

# Global instance
dynamic_ontology_builder = DynamicOntologyBuilder()