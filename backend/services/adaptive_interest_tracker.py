"""
Adaptive Interest Tracker - Cross-topic interest inference and discovery engine
"""
import asyncio
import math
from typing import Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, func
from datetime import datetime, timedelta

from db.models import Topic, UserInterest, UserSkillProgress, QuizQuestion, QuizSession


class AdaptiveInterestTracker:
    """
    Tracks user interests across the entire topic tree and infers hidden interests
    from behavior patterns and cross-topic relationships
    """
    
    def __init__(self):
        self.propagation_factor = 0.3  # How much interest propagates to related topics
        self.decay_rate = 0.95  # Daily interest decay to keep scores fresh
        self.discovery_threshold = 0.7  # Interest level needed to suggest new areas
        self.cross_topic_weight = 0.2  # Weight for cross-topic interest inference
        
    async def track_engagement_signals(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        action: str,  # answer, teach_me, skip, time_spent
        performance_data: Dict,
        context: Dict = None
    ):
        """
        Track all engagement signals and update interest across topic tree
        """
        
        # Calculate base interest signal
        base_signal = self._calculate_base_interest_signal(action, performance_data)
        
        # Update direct topic interest
        await self._update_direct_interest(db, user_id, topic_id, base_signal)
        
        # Propagate interest to related topics
        await self._propagate_interest_to_related_topics(
            db, user_id, topic_id, base_signal
        )
        
        # Infer cross-topic interests based on patterns
        await self._infer_cross_topic_interests(
            db, user_id, topic_id, action, performance_data
        )
        
        # Check for new interest discoveries
        new_interests = await self._discover_emerging_interests(db, user_id)
        
        # DISABLE TOPIC GENERATION: Interest tracker should NOT generate topics
        # Topic generation is handled by mastery-based system in dynamic_ontology_service
        # Interest tracker should only track interests, not trigger topic generation
        should_generate_topics = False
        
        # NOTE: Previously this had accuracy-based generation logic that bypassed 
        # the mastery level system, causing subtopics to be generated prematurely
        # at Novice level. All topic generation should go through the proper
        # mastery-based progression system only.
        
        generated_topics = []
        if should_generate_topics:
            # Import here to avoid circular imports
            from services.dynamic_ontology_service import dynamic_ontology_service
            generated_topics = await dynamic_ontology_service.check_and_unlock_subtopics(
                db, user_id, topic_id
            )
        
        await db.commit()
        
        return {
            'base_signal': base_signal,
            'new_interests_discovered': new_interests,
            'generated_topics': generated_topics
        }
    
    def _calculate_base_interest_signal(self, action: str, performance_data: Dict) -> float:
        """Calculate base interest signal from user action"""
        
        signals = {
            'teach_me': 0.15,     # Moderate interest but indicates struggle
            'skip': -0.4,         # Strong negative signal
            'repeat_topic': 0.1,     # Came back to topic
            'difficulty_increase': 0.2,  # Strong signal - seeking challenge
            'difficulty_decrease': -0.1  # Avoiding challenge
        }
        
        # Handle answer action based on correctness
        if action == 'answer':
            is_correct = performance_data.get('is_correct', None)
            if is_correct is True:
                base_signal = 0.3  # STRONG positive signal for correct answers
            elif is_correct is False:
                base_signal = 0.1  # Still engaging, trying to learn
            else:
                base_signal = 0.05  # Unknown correctness, small positive
        else:
            base_signal = signals.get(action, 0.0)
        
        # Adjust based on performance context (NO TIME-BASED ADJUSTMENTS)
        if performance_data:
            accuracy = performance_data.get('accuracy', 0.5)
            difficulty = performance_data.get('difficulty', 5)
            is_correct = performance_data.get('is_correct', None)
            
            # Strong bonus for correct answers on current question
            if is_correct is True:
                base_signal += 0.1  # Extra boost for getting current question right
            
            # Overall accuracy bonus (sustained performance)
            if accuracy > 0.8:
                base_signal += 0.1  # High sustained accuracy shows mastery/interest
            elif accuracy > 0.6:
                base_signal += 0.05  # Good sustained accuracy
                
            # Difficulty preference signals (challenge-seeking)
            if difficulty > 7 and is_correct:  # Handling hard questions well
                base_signal += 0.1
        
        # Clamp between -1 and 1
        return max(-1.0, min(1.0, base_signal))
    
    async def _update_direct_interest(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int, 
        signal: float
    ):
        """Update interest for the specific topic"""
        
        result = await db.execute(
            select(UserInterest).where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.topic_id == topic_id
                )
            )
        )
        
        interest = result.scalar_one_or_none()
        
        if not interest:
            interest = UserInterest(
                user_id=user_id,
                topic_id=topic_id,
                interest_score=0.5,  # Start neutral
                preference_type="inferred"
            )
            db.add(interest)
            await db.flush()
        
        # Update interest score directly (no decay toward 0.5)
        alpha = 0.2  # Learning rate for interest updates
        
        if signal > 0:
            # Positive signals: direct addition with diminishing returns
            interest.interest_score = min(1.0, interest.interest_score + signal * alpha)
        else:
            # Negative signals: direct subtraction  
            interest.interest_score = max(0.0, interest.interest_score + signal * alpha)
        
        # Update metadata
        if interest.interaction_count is None:
            interest.interaction_count = 0
        interest.interaction_count += 1
        interest.updated_at = datetime.utcnow()
        
        # Mark as explicit if strong signal
        if abs(signal) > 0.2:
            interest.preference_type = "explicit"
    
    async def _get_topic_interest_score(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ) -> Optional[float]:
        """Get current interest score for a topic"""
        result = await db.execute(
            select(UserInterest.interest_score).where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.topic_id == topic_id
                )
            )
        )
        score = result.scalar_one_or_none()
        return score
    
    async def _propagate_interest_to_related_topics(
        self,
        db: AsyncSession,
        user_id: int,
        source_topic_id: int,
        base_signal: float
    ):
        """Propagate interest signals to related topics in the ontology"""
        
        if abs(base_signal) < 0.05:  # Don't propagate weak signals
            return
            
        # Get topic relationships
        related_topics = await self._get_related_topics(db, source_topic_id)
        
        for related_topic_id, relationship_strength in related_topics.items():
            propagated_signal = base_signal * self.propagation_factor * relationship_strength
            
            if abs(propagated_signal) > 0.01:  # Only propagate meaningful signals
                await self._update_direct_interest(
                    db, user_id, related_topic_id, propagated_signal
                )
    
    async def _get_related_topics(self, db: AsyncSession, topic_id: int) -> Dict[int, float]:
        """Get related topics with relationship strengths"""
        
        related = {}
        
        # Get source topic
        source_result = await db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        source_topic = source_result.scalar_one_or_none()
        
        if not source_topic:
            return related
        
        # Parent topic (weaker relationship)
        if source_topic.parent_id:
            related[source_topic.parent_id] = 0.3
        
        # Sibling topics (same parent)
        if source_topic.parent_id:
            siblings_result = await db.execute(
                select(Topic.id).where(
                    and_(
                        Topic.parent_id == source_topic.parent_id,
                        Topic.id != topic_id
                    )
                )
            )
            for sibling in siblings_result.scalars():
                related[sibling] = 0.4
        
        # Child topics (stronger relationship)
        children_result = await db.execute(
            select(Topic.id).where(Topic.parent_id == topic_id)
        )
        for child in children_result.scalars():
            related[child] = 0.6
        
        # Semantic relationships (based on name similarity)
        semantic_related = await self._find_semantic_relationships(db, topic_id)
        for related_id, strength in semantic_related.items():
            if related_id not in related:
                related[related_id] = strength * 0.2  # Weaker than structural
        
        return related
    
    async def _find_semantic_relationships(self, db: AsyncSession, topic_id: int) -> Dict[int, float]:
        """Find semantically related topics based on name/description similarity"""
        
        # Get source topic
        source_result = await db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        source_topic = source_result.scalar_one_or_none()
        
        if not source_topic:
            return {}
        
        # Simple keyword-based semantic matching
        source_keywords = self._extract_keywords(source_topic.name, source_topic.description)
        
        # Get all other topics
        all_topics_result = await db.execute(
            select(Topic).where(Topic.id != topic_id)
        )
        
        semantic_related = {}
        
        for topic in all_topics_result.scalars():
            topic_keywords = self._extract_keywords(topic.name, topic.description)
            similarity = self._calculate_keyword_similarity(source_keywords, topic_keywords)
            
            if similarity > 0.3:  # Threshold for semantic relationship
                semantic_related[topic.id] = similarity
        
        return semantic_related
    
    def _extract_keywords(self, name: str, description: str) -> Set[str]:
        """Extract meaningful keywords from topic name and description"""
        
        text = f"{name} {description}".lower()
        
        # Common AI/ML keywords
        keywords = set()
        important_terms = [
            'learning', 'neural', 'network', 'deep', 'machine', 'algorithm',
            'classification', 'regression', 'clustering', 'supervised', 
            'unsupervised', 'reinforcement', 'computer', 'vision', 'language',
            'processing', 'natural', 'artificial', 'intelligence', 'data',
            'model', 'training', 'prediction', 'analysis', 'optimization'
        ]
        
        for term in important_terms:
            if term in text:
                keywords.add(term)
        
        # Extract other significant words (length > 4)
        words = text.split()
        for word in words:
            if len(word) > 4 and word.isalpha():
                keywords.add(word)
        
        return keywords
    
    def _calculate_keyword_similarity(self, keywords1: Set[str], keywords2: Set[str]) -> float:
        """Calculate similarity between two keyword sets"""
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _infer_cross_topic_interests(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        action: str,
        performance_data: Dict
    ):
        """Infer interests in other topics based on performance patterns"""
        
        # If user performs well in a topic, boost interest in related advanced topics
        if action == 'answer_correct' and performance_data.get('accuracy', 0) > 0.8:
            # Look for more advanced topics in the same domain
            await self._boost_advanced_topic_interest(db, user_id, topic_id)
        
        # If user shows interest (teach_me), explore adjacent domains
        if action == 'teach_me':
            await self._boost_adjacent_domain_interest(db, user_id, topic_id)
        
        # Pattern-based inference
        await self._apply_interest_patterns(db, user_id, topic_id, action, performance_data)
    
    async def _boost_advanced_topic_interest(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ):
        """Boost interest in more advanced topics in the same domain"""
        
        # Get current topic
        topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
        current_topic = topic_result.scalar_one_or_none()
        
        if not current_topic:
            return
        
        # Find topics with higher difficulty in related areas
        advanced_topics_result = await db.execute(
            select(Topic).where(
                and_(
                    Topic.difficulty_min > current_topic.difficulty_max,
                    or_(
                        Topic.parent_id == current_topic.parent_id,  # Siblings
                        Topic.parent_id == topic_id  # Children
                    )
                )
            )
        )
        
        for advanced_topic in advanced_topics_result.scalars():
            await self._update_direct_interest(
                db, user_id, advanced_topic.id, 0.08  # Small boost for advanced topics
            )
    
    async def _boost_adjacent_domain_interest(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ):
        """Boost interest in adjacent domains when user shows curiosity"""
        
        # Get semantic relationships and boost interest
        semantic_related = await self._find_semantic_relationships(db, topic_id)
        
        for related_id, similarity in semantic_related.items():
            boost = 0.06 * similarity  # Scale boost by similarity
            await self._update_direct_interest(db, user_id, related_id, boost)
    
    async def _apply_interest_patterns(
        self,
        db: AsyncSession,
        user_id: int,
        topic_id: int,
        action: str,
        performance_data: Dict
    ):
        """Apply learned patterns about user interests"""
        
        # Pattern: Users interested in practical applications
        if 'application' in performance_data.get('topic_name', '').lower():
            # Boost other application topics
            applications_result = await db.execute(
                select(Topic.id).where(
                    Topic.name.ilike('%application%')
                )
            )
            for app_topic_id in applications_result.scalars():
                if app_topic_id != topic_id:
                    await self._update_direct_interest(db, user_id, app_topic_id, 0.04)
        
        # Pattern: Users who like fundamentals also like theory
        if 'fundamental' in performance_data.get('topic_name', '').lower():
            theory_result = await db.execute(
                select(Topic.id).where(
                    or_(
                        Topic.name.ilike('%theory%'),
                        Topic.name.ilike('%principle%'),
                        Topic.name.ilike('%concept%')
                    )
                )
            )
            for theory_topic_id in theory_result.scalars():
                if theory_topic_id != topic_id:
                    await self._update_direct_interest(db, user_id, theory_topic_id, 0.03)
    
    async def _discover_emerging_interests(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> List[Dict]:
        """Discover new interests that have emerged from user behavior"""
        
        # Get topics with growing interest but low engagement
        emerging_result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, UserInterest.topic_id == Topic.id)
            .outerjoin(
                UserSkillProgress,
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.topic_id == Topic.id
                )
            )
            .where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.interest_score > self.discovery_threshold,
                    or_(
                        UserSkillProgress.questions_answered.is_(None),
                        UserSkillProgress.questions_answered < 3
                    )
                )
            )
        )
        
        emerging_interests = []
        for interest, topic in emerging_result:
            emerging_interests.append({
                'topic_id': topic.id,
                'topic_name': topic.name,
                'interest_score': interest.interest_score,
                'discovery_reason': 'inferred_from_behavior'
            })
        
        return emerging_interests
    
    async def get_interest_insights(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict:
        """Get comprehensive insights about user's interests and patterns"""
        
        # Get all user interests
        interests_result = await db.execute(
            select(UserInterest, Topic)
            .join(Topic, UserInterest.topic_id == Topic.id)
            .where(UserInterest.user_id == user_id)
            .order_by(UserInterest.interest_score.desc())
        )
        
        interests_data = interests_result.fetchall()
        
        # Categorize interests
        high_interest = []
        growing_interest = []
        declining_interest = []
        
        for interest, topic in interests_data:
            interest_info = {
                'topic_id': topic.id,
                'topic_name': topic.name,
                'interest_score': interest.interest_score,
                'preference_type': interest.preference_type,
                'last_updated': interest.updated_at
            }
            
            if interest.interest_score > 0.7:
                high_interest.append(interest_info)
            elif interest.interest_score > 0.5:
                growing_interest.append(interest_info)
            else:
                declining_interest.append(interest_info)
        
        # Get learning patterns
        patterns = await self._analyze_learning_patterns(db, user_id)
        
        return {
            'high_interest_topics': high_interest[:5],
            'growing_interest_topics': growing_interest[:5],
            'declining_interest_topics': declining_interest[:3],
            'learning_patterns': patterns,
            'total_topics_explored': len(interests_data),
            'interest_diversity': self._calculate_interest_diversity(interests_data)
        }
    
    async def _analyze_learning_patterns(self, db: AsyncSession, user_id: int) -> Dict:
        """Analyze user's learning patterns and preferences"""
        
        # Get user's quiz history
        quiz_data_result = await db.execute(
            select(
                QuizQuestion.user_action,
                QuizQuestion.time_spent,
                QuizQuestion.is_correct,
                Topic.difficulty_min,
                Topic.difficulty_max
            )
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .join(Topic, QuizSession.topic_id == Topic.id)
            .where(QuizSession.user_id == user_id)
            .order_by(QuizQuestion.answered_at.desc())
            .limit(50)  # Recent history
        )
        
        quiz_data = quiz_data_result.fetchall()
        
        if not quiz_data:
            return {}
        
        # Analyze patterns
        teach_me_ratio = sum(1 for row in quiz_data if row[0] == 'teach_me') / len(quiz_data)
        skip_ratio = sum(1 for row in quiz_data if row[0] == 'skip') / len(quiz_data)
        avg_time_spent = sum(row[1] or 0 for row in quiz_data) / len(quiz_data)
        accuracy = sum(1 for row in quiz_data if row[2]) / len(quiz_data)
        
        # Difficulty preference
        difficulties = [row[3] for row in quiz_data if row[3]]
        avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 5
        
        return {
            'curiosity_level': teach_me_ratio,  # High = likes to explore
            'focus_level': 1 - skip_ratio,     # High = doesn't skip much
            'engagement_time': avg_time_spent,
            'accuracy_trend': accuracy,
            'difficulty_preference': avg_difficulty,
            'learning_style': self._infer_learning_style(teach_me_ratio, skip_ratio, avg_time_spent)
        }
    
    def _infer_learning_style(self, teach_me_ratio: float, skip_ratio: float, avg_time: float) -> str:
        """Infer user's learning style from behavior patterns"""
        
        if teach_me_ratio > 0.3:
            return "explorer"  # Likes to discover new things
        elif skip_ratio < 0.1 and avg_time > 20:
            return "deep_learner"  # Thorough and methodical
        elif skip_ratio > 0.3:
            return "efficiency_focused"  # Wants to get through quickly
        elif avg_time < 10:
            return "quick_learner"  # Fast but engaged
        else:
            return "balanced"  # Balanced approach
    
    def _calculate_interest_diversity(self, interests_data: List) -> float:
        """Calculate how diverse the user's interests are"""
        
        if len(interests_data) < 2:
            return 0.0
        
        # Calculate entropy of interest distribution
        total_interest = sum(interest.interest_score for interest, _ in interests_data)
        if total_interest == 0:
            return 0.0
        
        entropy = 0
        for interest, _ in interests_data:
            if interest.interest_score > 0:
                p = interest.interest_score / total_interest
                entropy -= p * math.log2(p)
        
        # Normalize by maximum possible entropy
        max_entropy = math.log2(len(interests_data))
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    async def decay_interests(self, db: AsyncSession, user_id: int):
        """Apply daily decay to interests to keep them fresh"""
        
        await db.execute(
            update(UserInterest)
            .where(UserInterest.user_id == user_id)
            .values(
                interest_score=UserInterest.interest_score * self.decay_rate
            )
        )
        
        await db.commit()


# Global instance
adaptive_interest_tracker = AdaptiveInterestTracker()