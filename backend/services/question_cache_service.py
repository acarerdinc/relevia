"""
Question Cache Service - Handles question prefetching and pool management
"""
import asyncio
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from core.logging_config import logger


class QuestionCacheService:
    """
    Centralized service for managing question caching, prefetching, and pool optimization
    """
    
    def __init__(self):
        # Prefetch cache: {session_id: prefetched_question_data}
        self.prefetch_cache = {}
        self.prefetch_tasks = {}  # Track ongoing prefetch tasks
        
        # Question pool cache: {topic_id: [question_data, ...]}
        self.question_pools = {}
        self.pool_generation_tasks = {}  # Track ongoing pool generation
        self.min_pool_size = 3  # Minimum questions to keep per topic pool
    
    def has_prefetched_question(self, session_id: int) -> bool:
        """Check if we have a prefetched question for this session"""
        return session_id in self.prefetch_cache
    
    def get_prefetched_question(self, session_id: int) -> Optional[Dict]:
        """Get and remove prefetched question from cache"""
        return self.prefetch_cache.pop(session_id, None)
    
    async def prefetch_next_question(self, user_id: int, session_id: int):
        """
        Prefetch the next question in background for instant loading
        """
        # Avoid duplicate prefetch tasks
        if session_id in self.prefetch_tasks:
            return
        
        try:
            # Import here to avoid circular imports
            from services.adaptive_question_selector import adaptive_question_selector
            from db.database import AsyncSessionLocal
            
            logger.info(f"Starting prefetch for session {session_id}")
            
            # Mark as in progress
            self.prefetch_tasks[session_id] = True
            
            async with AsyncSessionLocal() as db:
                # Get next question using the selector
                question_data = await adaptive_question_selector.select_next_question(
                    db, user_id, session_id
                )
                
                if question_data:
                    # Store in cache for instant retrieval
                    self.prefetch_cache[session_id] = question_data
                    logger.info(f"Successfully prefetched question for session {session_id}")
                else:
                    logger.warning(f"No question available to prefetch for session {session_id}")
                    
        except Exception as e:
            logger.error(f"Error prefetching question for session {session_id}: {e}")
        finally:
            # Clean up task tracking
            self.prefetch_tasks.pop(session_id, None)
    
    async def ensure_question_pool(self, db: AsyncSession, topic_id: int, user_id: int):
        """
        Ensure we have sufficient questions in the pool for this topic
        """
        # Check current pool size
        current_pool = self.question_pools.get(topic_id, [])
        
        if len(current_pool) >= self.min_pool_size:
            return  # Pool is sufficient
        
        # Avoid duplicate pool generation
        if topic_id in self.pool_generation_tasks:
            return
        
        try:
            from services.adaptive_question_selector import adaptive_question_selector
            
            self.pool_generation_tasks[topic_id] = True
            logger.info(f"Generating question pool for topic {topic_id}")
            
            # Generate additional questions for the pool
            questions_needed = self.min_pool_size - len(current_pool)
            
            for _ in range(questions_needed):
                question_data = await adaptive_question_selector.select_next_question(
                    db, user_id, None, topic_id_override=topic_id
                )
                
                if question_data:
                    current_pool.append(question_data)
            
            # Update pool cache
            self.question_pools[topic_id] = current_pool
            logger.info(f"Pool for topic {topic_id} now has {len(current_pool)} questions")
            
        except Exception as e:
            logger.error(f"Error generating question pool for topic {topic_id}: {e}")
        finally:
            self.pool_generation_tasks.pop(topic_id, None)
    
    def get_pool_question(self, topic_id: int) -> Optional[Dict]:
        """Get a question from the topic pool if available"""
        pool = self.question_pools.get(topic_id, [])
        if pool:
            return pool.pop(0)  # FIFO
        return None
    
    def clear_session_cache(self, session_id: int):
        """Clear all cached data for a session"""
        self.prefetch_cache.pop(session_id, None)
        self.prefetch_tasks.pop(session_id, None)
    
    def clear_topic_pool(self, topic_id: int):
        """Clear the question pool for a topic"""
        self.question_pools.pop(topic_id, None)
        self.pool_generation_tasks.pop(topic_id, None)


# Global instance
question_cache_service = QuestionCacheService()