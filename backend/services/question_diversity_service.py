"""
Question Diversity Service - Prevents semantic repetition in question generation
"""
import re
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from collections import Counter

from db.models import TopicQuestionHistory, Question, QuizQuestion, QuizSession
from core.logging_config import logger


class QuestionDiversityService:
    """
    Service to ensure semantic diversity in question generation
    Prevents AI from obsessing over specific themes like "Transformer architecture"
    """
    
    def __init__(self):
        # Define key concept patterns for different topics
        self.concept_patterns = {
            'transformer': ['transformer', 'attention', 'bert', 'gpt', 'self-attention', 'encoder', 'decoder'],
            'neural_network': ['neural', 'network', 'neuron', 'layer', 'weight', 'bias', 'activation'],
            'cnn': ['convolution', 'cnn', 'filter', 'kernel', 'pooling', 'feature map'],
            'rnn': ['rnn', 'lstm', 'gru', 'recurrent', 'sequence', 'memory'],
            'reinforcement': ['reward', 'policy', 'agent', 'environment', 'q-learning', 'value function'],
            'supervised': ['supervised', 'labeled', 'classification', 'regression', 'training data'],
            'unsupervised': ['unsupervised', 'clustering', 'dimensionality', 'pca', 'k-means'],
            'computer_vision': ['image', 'vision', 'pixel', 'detection', 'segmentation', 'recognition'],
            'nlp': ['text', 'language', 'word', 'sentence', 'token', 'embedding', 'nlp']
        }
        
        # Cooldown periods for concepts (in questions)
        self.concept_cooldown = {
            'high_frequency': 3,    # Popular concepts need 3 questions gap
            'medium_frequency': 2,  # Medium concepts need 2 questions gap  
            'low_frequency': 1      # Rare concepts need 1 question gap
        }
    
    async def extract_question_concepts(self, question_text: str) -> List[str]:
        """
        Extract key concepts from a question using pattern matching
        Returns list of detected concepts/themes
        """
        question_lower = question_text.lower()
        detected_concepts = []
        
        # Check each concept pattern
        for concept_group, patterns in self.concept_patterns.items():
            for pattern in patterns:
                if pattern in question_lower:
                    detected_concepts.append(concept_group)
                    break  # Don't double-count the same concept group
        
        # Extract additional keywords using simple NLP
        # Focus on nouns and technical terms
        technical_words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', question_text)  # PascalCase
        technical_words += re.findall(r'\b[a-z]+(?:-[a-z]+)+\b', question_lower)  # hyphenated terms
        
        # Filter to likely technical concepts (3+ chars, not common words)
        common_words = {'the', 'and', 'for', 'are', 'with', 'this', 'that', 'from', 'they', 'have', 'would', 'what', 'which'}
        for word in technical_words:
            if len(word) >= 3 and word.lower() not in common_words:
                detected_concepts.append(word.lower())
        
        return list(set(detected_concepts))  # Remove duplicates
    
    async def get_recent_question_history(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent question history for a user and topic
        Used to provide context to AI and avoid repetition
        """
        # Get recent questions from question history
        history_result = await db.execute(
            select(TopicQuestionHistory)
            .where(
                and_(
                    TopicQuestionHistory.user_id == user_id,
                    TopicQuestionHistory.topic_id == topic_id
                )
            )
            .order_by(desc(TopicQuestionHistory.asked_at))
            .limit(limit)
        )
        
        history_records = history_result.scalars().all()
        
        recent_questions = []
        for record in history_records:
            recent_questions.append({
                'question': record.question_content,
                'concepts': record.extracted_concepts or [],
                'asked_at': record.asked_at
            })
        
        return recent_questions
    
    async def check_concept_diversity(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        proposed_concepts: List[str]
    ) -> Dict:
        """
        Check if proposed concepts are too similar to recent questions
        Returns diversity score and recommendations
        """
        # Get recent question history
        recent_history = await self.get_recent_question_history(db, user_id, topic_id, limit=8)
        
        if not recent_history:
            return {
                'is_diverse': True,
                'diversity_score': 1.0,
                'reason': 'no_recent_history',
                'recommendations': []
            }
        
        # Count recent concept frequency
        recent_concepts = []
        for question in recent_history:
            recent_concepts.extend(question.get('concepts', []))
        
        concept_frequency = Counter(recent_concepts)
        
        # Check for overlap with proposed concepts
        overlapping_concepts = []
        total_overlap_score = 0
        
        for concept in proposed_concepts:
            if concept in concept_frequency:
                frequency = concept_frequency[concept]
                # Higher frequency = higher penalty
                overlap_penalty = min(frequency * 0.3, 1.0)
                total_overlap_score += overlap_penalty
                overlapping_concepts.append({
                    'concept': concept,
                    'frequency': frequency,
                    'penalty': overlap_penalty
                })
        
        # Calculate diversity score (higher = more diverse)
        max_possible_overlap = len(proposed_concepts)
        diversity_score = max(0, 1.0 - (total_overlap_score / max(max_possible_overlap, 1)))
        
        # Determine if diverse enough (threshold: 0.4)
        is_diverse = diversity_score >= 0.4
        
        # Generate recommendations for improvement
        recommendations = []
        if not is_diverse:
            # Find under-represented concept areas
            all_concept_groups = set(self.concept_patterns.keys())
            recent_concept_groups = set(recent_concepts)
            underused_groups = all_concept_groups - recent_concept_groups
            
            if underused_groups:
                recommendations.append(f"Focus on underexplored areas: {', '.join(list(underused_groups)[:3])}")
            
            if overlapping_concepts:
                overused = [c['concept'] for c in overlapping_concepts if c['frequency'] >= 2]
                if overused:
                    recommendations.append(f"Avoid recently covered concepts: {', '.join(overused[:3])}")
        
        return {
            'is_diverse': is_diverse,
            'diversity_score': diversity_score,
            'overlapping_concepts': overlapping_concepts,
            'recent_concept_frequency': dict(concept_frequency.most_common(5)),
            'recommendations': recommendations
        }
    
    async def record_question_asked(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        question_id: int,
        session_id: int,
        question_content: str
    ):
        """
        Record that a question was asked and extract its concepts
        """
        try:
            # Extract concepts from the question
            concepts = await self.extract_question_concepts(question_content)
            
            # Create history record
            history_record = TopicQuestionHistory(
                user_id=user_id,
                topic_id=topic_id,
                question_id=question_id,
                session_id=session_id,
                question_content=question_content,
                extracted_concepts=concepts
            )
            
            db.add(history_record)
            await db.commit()
            
            logger.info(f"Recorded question history for user {user_id}, topic {topic_id}: {len(concepts)} concepts extracted")
            
        except Exception as e:
            logger.error(f"Error recording question history: {e}")
            await db.rollback()
    
    async def generate_diversity_prompt_context(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        topic_name: str
    ) -> str:
        """
        Generate context for AI prompt to encourage diverse question generation
        """
        # Get recent question history
        recent_history = await self.get_recent_question_history(db, user_id, topic_id, limit=5)
        
        if not recent_history:
            return f"This is the first question about {topic_name}. Provide a broad, foundational question to introduce the topic."
        
        # Build context showing recent questions and concepts
        context_parts = [f"Recent questions asked about {topic_name}:"]
        
        recent_concepts = []
        for i, question in enumerate(recent_history, 1):
            # Show only question content, not concepts (to avoid over-constraining AI)
            context_parts.append(f"{i}. {question['question']}")
            recent_concepts.extend(question.get('concepts', []))
        
        # Identify overused concepts
        concept_frequency = Counter(recent_concepts)
        overused_concepts = [concept for concept, freq in concept_frequency.most_common(3) if freq >= 2]
        
        if overused_concepts:
            context_parts.append(f"\nAVOID these recently covered themes: {', '.join(overused_concepts)}")
        
        # Suggest unexplored areas
        all_topic_concepts = []
        for concept_group in self.concept_patterns.keys():
            if concept_group not in recent_concepts:
                all_topic_concepts.append(concept_group)
        
        if all_topic_concepts:
            context_parts.append(f"\nCONSIDER exploring these unexplored aspects of {topic_name}: {', '.join(all_topic_concepts[:3])}")
        
        context_parts.append(f"\nCreate a question that covers NEW aspects of {topic_name}, different from the recent questions above.")
        
        return "\n".join(context_parts)
    
    async def cleanup_old_history(self, db: AsyncSession, days_to_keep: int = 30):
        """
        Clean up old question history records to prevent database bloat
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old records
            from sqlalchemy import delete
            result = await db.execute(
                delete(TopicQuestionHistory)
                .where(TopicQuestionHistory.asked_at < cutoff_date)
            )
            
            deleted_count = result.rowcount
            await db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old question history records")
            
        except Exception as e:
            logger.error(f"Error cleaning up question history: {e}")
            await db.rollback()


# Global instance
question_diversity_service = QuestionDiversityService()