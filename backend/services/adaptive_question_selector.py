"""
Adaptive Question Selector - Multi-Armed Bandit approach for exploration/exploitation
"""
import math
import random
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from datetime import datetime, timedelta

from db.models import (
    Topic, Question, UserSkillProgress, UserInterest, 
    QuizSession, QuizQuestion
)
from services.gemini_service import gemini_service


class AdaptiveQuestionSelector:
    """
    Implements Multi-Armed Bandit algorithm for intelligent question selection
    Each topic is an "arm" - we balance exploration of new topics vs exploitation of engaging ones
    """
    
    def __init__(self):
        self.exploration_rate = 0.2  # 20% exploration, 80% exploitation
        self.confidence_multiplier = 2.0  # UCB confidence parameter
        self.interest_weight = 0.4  # How much to weight interest vs proficiency
        self.proficiency_weight = 0.3
        self.discovery_weight = 0.3  # Bonus for unexplored topics
        
    async def select_next_question(
        self, 
        db: AsyncSession, 
        user_id: int,
        current_session_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Select the next question using exploration/exploitation strategy
        Returns question data or None if no suitable questions found
        """
        
        # Get all unlocked topics for user
        unlocked_topics = await self._get_unlocked_topics(db, user_id)
        if not unlocked_topics:
            return None
            
        # Calculate topic scores using Multi-Armed Bandit
        topic_scores = await self._calculate_topic_scores(db, user_id, unlocked_topics)
        
        # For infinite learning, always try to generate fresh questions first
        # This ensures we never run out of content
        
        # Select the best topic using exploration/exploitation
        selected_topic = await self._select_topic_with_strategy(topic_scores)
        
        if selected_topic:
            # First, try to generate a new question for this topic
            print(f"Generating fresh question for top-rated topic: {selected_topic['name']}")
            generated_question = await self._generate_question_for_topic(db, user_id, selected_topic)
            
            if generated_question:
                print(f"Successfully generated fresh question for topic {selected_topic['name']}")
                await self._update_topic_selection_stats(db, user_id, selected_topic['id'])
                return generated_question
            
            # If generation fails, try existing questions
            print(f"Generation failed, trying existing questions for topic {selected_topic['name']}")
            question_data = await self._get_question_from_topic(
                db, user_id, selected_topic, current_session_id
            )
            
            if question_data:
                await self._update_topic_selection_stats(db, user_id, selected_topic['id'])
                return question_data
        
        # If top topic doesn't work, try backup topics
        print(f"Top topic failed, trying backup topics for user {user_id}")
        attempted_topics = set()
        if selected_topic:
            attempted_topics.add(selected_topic['id'])
        
        max_attempts = min(5, len(topic_scores))
        for attempt in range(max_attempts):
            available_topic_scores = [t for t in topic_scores if t['id'] not in attempted_topics]
            
            if not available_topic_scores:
                break
                
            backup_topic = await self._select_topic_with_strategy(available_topic_scores)
            
            if not backup_topic:
                break
                
            attempted_topics.add(backup_topic['id'])
            
            # Try generating for backup topic
            generated_question = await self._generate_question_for_topic(db, user_id, backup_topic)
            
            if generated_question:
                await self._update_topic_selection_stats(db, user_id, backup_topic['id'])
                return generated_question
            
            # Try existing questions for backup topic
            question_data = await self._get_question_from_topic(
                db, user_id, backup_topic, current_session_id
            )
            
            if question_data:
                await self._update_topic_selection_stats(db, user_id, backup_topic['id'])
                return question_data
            
        # As final fallback, try any available question (ignoring recently asked filter)
        print(f"All generation attempts failed, using any available question for user {user_id}")
        
        for topic in topic_scores[:3]:
            question_data = await self._get_question_from_topic(
                db, user_id, topic, None  # Pass None for session_id to disable recently-asked filter
            )
            
            if question_data:
                # Mark this as a fallback question
                question_data['is_fallback'] = True
                question_data['fallback_reason'] = 'generation_failed'
                await self._update_topic_selection_stats(db, user_id, topic['id'])
                return question_data
        
        return None
    
    async def _get_unlocked_topics(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """Get all topics unlocked for the user with their stats"""
        
        result = await db.execute(
            select(
                Topic,
                UserSkillProgress.questions_answered,
                UserSkillProgress.correct_answers,
                UserSkillProgress.skill_level,
                UserSkillProgress.confidence,
                UserSkillProgress.mastery_level
            )
            .join(UserSkillProgress, Topic.id == UserSkillProgress.topic_id)
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        
        topics = []
        for topic, questions_answered, correct_answers, skill_level, confidence, mastery_level in result:
            # Calculate available question count
            question_count_result = await db.execute(
                select(func.count(Question.id))
                .where(Question.topic_id == topic.id)
            )
            total_questions = question_count_result.scalar() or 0
            
            topics.append({
                'id': topic.id,
                'name': topic.name,
                'description': topic.description,
                'difficulty_min': topic.difficulty_min,
                'difficulty_max': topic.difficulty_max,
                'questions_answered': questions_answered or 0,
                'correct_answers': correct_answers or 0,
                'skill_level': skill_level or 0.5,
                'confidence': confidence or 0.5,
                'mastery_level': mastery_level or 'novice',
                'total_questions': total_questions,
                'accuracy': (correct_answers / questions_answered) if questions_answered > 0 else 0.0
            })
            
        return topics
    
    async def _calculate_topic_scores(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topics: List[Dict]
    ) -> List[Dict]:
        """Calculate UCB scores for each topic"""
        
        # Get user interests
        interest_result = await db.execute(
            select(UserInterest)
            .where(UserInterest.user_id == user_id)
        )
        interests = {
            interest.topic_id: interest.interest_score 
            for interest in interest_result.scalars().all()
        }
        
        # Get the most recently answered topic for continuity
        recent_topic_result = await db.execute(
            select(Question.topic_id)
            .join(QuizQuestion, Question.id == QuizQuestion.question_id)
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .where(QuizSession.user_id == user_id)
            .order_by(QuizQuestion.answered_at.desc())
            .limit(1)
        )
        recent_topic_id = recent_topic_result.scalar_one_or_none()
        
        # Get total selections across all topics for confidence calculation
        total_selections = sum(topic['questions_answered'] for topic in topics)
        if total_selections == 0:
            total_selections = 1  # Avoid division by zero
            
        scored_topics = []
        
        for topic in topics:
            topic_id = topic['id']
            selections = max(1, topic['questions_answered'])  # Avoid log(0)
            
            # Base reward: combination of interest, proficiency, and engagement
            interest_score = interests.get(topic_id, 0.5)  # Default neutral interest
            proficiency_score = topic['skill_level']
            
            # Discovery bonus for less explored topics
            exploration_bonus = 1.0 / (1.0 + selections * 0.1)
            
            # RECENCY BOOST: Strong preference for continuing where user left off
            recency_bonus = 0.0
            if recent_topic_id and topic_id == recent_topic_id:
                recency_bonus = 0.5  # STRONG bonus for continuity
            
            # SPECIALIZATION BOOST: Favor subtopics ONLY when user has mastered parent
            specialization_bonus = 0.0
            if topic.get('name') != "Artificial Intelligence":  # Not the root topic
                # Check user's mastery of this topic
                accuracy = topic.get('accuracy', 0)
                if accuracy < 0.6:  # Struggling with this topic
                    specialization_bonus = -0.1  # Slight penalty - need more practice
                elif selections <= 3:  # New topic with good performance
                    specialization_bonus = 0.3  # Moderate bonus for exploration
                else:
                    specialization_bonus = 0.2  # Small bonus for variety
            else:
                # Root topic: check if user has sufficient foundation
                if topic.get('questions_answered', 0) < 5:
                    specialization_bonus = 0.1  # Slight bonus - build foundation first
                elif len(topics) > 1 and topic.get('accuracy', 0) >= 0.6:
                    specialization_bonus = -0.2  # Ready to move deeper
            
            # Calculate base reward with specialization and recency boosts
            base_reward = (
                self.interest_weight * interest_score +
                self.proficiency_weight * proficiency_score +
                self.discovery_weight * exploration_bonus +
                0.3 * specialization_bonus +  # 30% weight for specialization
                0.4 * recency_bonus  # 40% weight for continuity - VERY important
            )
            
            # UCB confidence interval
            confidence = self.confidence_multiplier * math.sqrt(
                math.log(total_selections) / selections
            )
            
            # Final UCB score
            ucb_score = base_reward + confidence
            
            scored_topics.append({
                **topic,
                'interest_score': interest_score,
                'base_reward': base_reward,
                'confidence': confidence,
                'ucb_score': ucb_score,
                'exploration_bonus': exploration_bonus,
                'specialization_bonus': specialization_bonus,
                'recency_bonus': recency_bonus,
                'is_recent': topic_id == recent_topic_id
            })
            
        # Sort by UCB score (highest first)
        scored_topics.sort(key=lambda x: x['ucb_score'], reverse=True)
        
        return scored_topics
    
    async def _select_topic_with_strategy(self, scored_topics: List[Dict]) -> Optional[Dict]:
        """Select topic using exploration/exploitation strategy"""
        
        if not scored_topics:
            return None
            
        # For infinite learning, all unlocked topics are available 
        # (questions are generated on-demand)
        available_topics = scored_topics
        
        if not available_topics:
            return None
            
        # Exploration vs Exploitation decision
        if random.random() < self.exploration_rate:
            # EXPLORATION: Randomly select from less explored topics
            # Weight by exploration bonus (favor less explored)
            exploration_weights = [topic['exploration_bonus'] for topic in available_topics]
            selected_topic = random.choices(available_topics, weights=exploration_weights)[0]
        else:
            # EXPLOITATION: Select highest UCB score
            selected_topic = available_topics[0]
            
        return selected_topic
    
    async def _get_question_from_topic(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic: Dict,
        current_session_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Get a question from the selected topic, avoiding recently asked ones"""
        
        topic_id = topic['id']
        
        # Get recently asked questions across ALL sessions for this user (not just current session)
        # This ensures we don't repeat questions the user has already seen
        recently_asked = set()
        recent_result = await db.execute(
            select(QuizQuestion.question_id)
            .join(QuizSession, QuizQuestion.quiz_session_id == QuizSession.id)
            .where(QuizSession.user_id == user_id)
        )
        recently_asked = {row[0] for row in recent_result.fetchall()}
        
        # Get available questions from topic, excluding recently asked ones
        # Only select questions with valid options (for multiple choice)
        query = select(Question).where(
            Question.topic_id == topic_id,
            Question.options.isnot(None)
        )
        if recently_asked:
            query = query.where(~Question.id.in_(recently_asked))
            
        result = await db.execute(query)
        available_questions = result.scalars().all()
        
        # If no questions available from this topic (all have been asked), 
        # return None to let the selector try a different topic
        if not available_questions:
            return None
            
        # Select question based on user's current skill level AND topic depth
        # Deeper topics should have harder questions
        user_skill = topic['skill_level']
        
        # Calculate topic depth (how deep in the tree)
        topic_depth = await self._get_topic_depth(db, topic_id)
        
        # Base difficulty on skill level
        base_difficulty = int(user_skill * 10)
        
        # Add depth bonus: deeper topics are inherently more complex
        depth_bonus = min(3, topic_depth - 1)  # +1 difficulty per level, max +3
        
        # Add some randomness for variety
        random_adjustment = random.randint(-1, 2)
        
        target_difficulty = min(10, max(1, base_difficulty + depth_bonus + random_adjustment))
        
        # Find questions close to target difficulty
        suitable_questions = [
            q for q in available_questions 
            if abs(q.difficulty - target_difficulty) <= 2
        ]
        
        if not suitable_questions:
            suitable_questions = available_questions
            
        # Randomly select from suitable questions
        selected_question = random.choice(suitable_questions)
        
        # Ensure options is a valid list
        options = selected_question.options if selected_question.options else []
        
        return {
            'question_id': selected_question.id,
            'question': selected_question.content,
            'options': options,
            'difficulty': selected_question.difficulty,
            'topic_id': topic_id,
            'topic_name': topic['name'],
            'selection_strategy': 'exploration' if random.random() < self.exploration_rate else 'exploitation',
            'topic_ucb_score': topic.get('ucb_score', 0),
            'topic_interest_score': topic.get('interest_score', 0.5)
        }
    
    async def _update_topic_selection_stats(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int
    ):
        """Update statistics for topic selection (for future UCB calculations)"""
        
        # This is handled by existing question answering flow
        # The selection count is tracked via questions_answered in UserSkillProgress
        pass
    
    async def update_topic_rewards(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic_id: int,
        engagement_signal: float,
        learning_progress: float
    ):
        """
        Update topic reward based on user engagement and learning progress
        Called after user answers a question
        """
        
        # Calculate reward based on multiple factors
        reward = (
            0.4 * engagement_signal +      # How engaged was user?
            0.4 * learning_progress +      # Did they learn/improve?
            0.2 * random.random()          # Small random component
        )
        
        # Store this in UserInterest as a running average
        # This will be used in future UCB calculations
        result = await db.execute(
            select(UserInterest).where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.topic_id == topic_id
                )
            )
        )
        
        interest = result.scalar_one_or_none()
        if interest:
            # Update as running average
            alpha = 0.1  # Learning rate
            interest.interest_score = (
                (1 - alpha) * interest.interest_score + 
                alpha * reward
            )
            interest.updated_at = datetime.utcnow()
        
        await db.commit()
    
    async def _get_topic_depth(self, db: AsyncSession, topic_id: int) -> int:
        """Calculate how deep a topic is in the ontology tree"""
        depth = 0
        current_id = topic_id
        
        # Traverse up the tree to count depth
        while current_id:
            result = await db.execute(
                select(Topic.parent_id).where(Topic.id == current_id)
            )
            parent_id = result.scalar_one_or_none()
            
            if parent_id:
                depth += 1
                current_id = parent_id
            else:
                break
                
        return depth
    
    async def get_exploration_stats(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> Dict:
        """Get user's exploration and discovery statistics"""
        
        # Get topic coverage
        unlocked_count_result = await db.execute(
            select(func.count(UserSkillProgress.id))
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.is_unlocked == True
                )
            )
        )
        unlocked_count = unlocked_count_result.scalar() or 0
        
        # Get total available topics
        total_topics_result = await db.execute(select(func.count(Topic.id)))
        total_topics = total_topics_result.scalar() or 1
        
        # Get recent discovery rate (new topics unlocked in last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_discoveries_result = await db.execute(
            select(func.count(UserSkillProgress.id))
            .where(
                and_(
                    UserSkillProgress.user_id == user_id,
                    UserSkillProgress.unlocked_at >= week_ago
                )
            )
        )
        recent_discoveries = recent_discoveries_result.scalar() or 0
        
        # Get engagement diversity (how spread out the learning is)
        topic_engagement_result = await db.execute(
            select(
                UserSkillProgress.topic_id,
                UserSkillProgress.questions_answered
            )
            .where(UserSkillProgress.user_id == user_id)
        )
        
        engagement_data = topic_engagement_result.fetchall()
        if engagement_data:
            total_questions = sum(row[1] or 0 for row in engagement_data)
            if total_questions > 0:
                # Calculate engagement entropy (higher = more diverse)
                entropy = 0
                for _, questions in engagement_data:
                    if questions and questions > 0:
                        p = questions / total_questions
                        entropy -= p * math.log2(p)
            else:
                entropy = 0
        else:
            entropy = 0
        
        return {
            'topics_unlocked': unlocked_count,
            'total_topics': total_topics,
            'exploration_coverage': unlocked_count / total_topics,
            'recent_discoveries': recent_discoveries,
            'engagement_diversity': entropy,
            'discovery_rate': recent_discoveries / 7  # Per day
        }
    
    async def _generate_question_for_topic(
        self, 
        db: AsyncSession, 
        user_id: int, 
        topic: Dict
    ) -> Optional[Dict]:
        """Generate a new question for the given topic using AI"""
        
        try:
            # Get user's skill level AND topic depth for difficulty
            user_skill = topic.get('skill_level', 0.5)
            
            # Calculate topic depth for difficulty adjustment
            topic_depth = await self._get_topic_depth(db, topic['id'])
            
            # Base difficulty on skill and depth
            base_difficulty = int(user_skill * 10)
            depth_bonus = min(3, topic_depth - 1)  # Deeper = harder
            
            target_difficulty = min(10, max(1, base_difficulty + depth_bonus + random.randint(-1, 2)))
            
            # Generate question using Gemini
            prompt = f"""Create a multiple-choice question about {topic['name']}.

Topic: {topic['name']}
Description: {topic.get('description', 'No description available')}
Difficulty level: {target_difficulty}/10
User skill level: {user_skill:.2f}

Requirements:
- Create a clear, educational question appropriate for difficulty level {target_difficulty}
- Provide exactly 4 multiple choice options
- Write an explanation that stands alone and doesn't reference A/B/C/D options
- The explanation should be 2-3 sentences that clearly state the correct answer and explain why
- Focus on teaching the concept, not just stating which option was correct

Format your response as JSON:
{{
    "question": "Your question here",
    "options": ["Option 1 text", "Option 2 text", "Option 3 text", "Option 4 text"],
    "correct_answer": "C",
    "explanation": "The correct answer is [restate the correct answer in full]. This is because [brief, clear explanation of the concept without referencing option letters]."
}}

Example explanation format:
"The correct answer is 'Machine learning algorithms that learn from labeled data'. Supervised learning requires a training dataset where each example has a known output, allowing the algorithm to learn the mapping between inputs and outputs."

Make sure the explanation:
- Restates the correct answer in full
- Explains the concept clearly
- Doesn't use phrases like "Option A" or "Choice B"
- Teaches the user something valuable about the topic"""

            response = await gemini_service.generate_content(prompt)
            
            if not response:
                print(f"Failed to generate question content for topic {topic['name']}")
                return None
            
            # Parse the JSON response (handle markdown code blocks)
            import json
            import re
            
            try:
                # Remove markdown code block wrapper if present
                json_content = response.strip()
                if json_content.startswith('```json'):
                    json_content = re.sub(r'^```json\s*', '', json_content)
                    json_content = re.sub(r'\s*```$', '', json_content)
                elif json_content.startswith('```'):
                    json_content = re.sub(r'^```\s*', '', json_content)
                    json_content = re.sub(r'\s*```$', '', json_content)
                
                question_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response for topic {topic['name']}: {response}")
                print(f"JSON error: {str(e)}")
                return None
            
            # Validate the response structure
            required_fields = ['question', 'options', 'correct_answer', 'explanation']
            if not all(field in question_data for field in required_fields):
                print(f"Invalid question structure for topic {topic['name']}: {question_data}")
                return None
            
            if len(question_data['options']) != 4:
                print(f"Invalid number of options for topic {topic['name']}: {len(question_data['options'])}")
                return None
            
            # Convert answer format if needed (A/B/C/D -> full option text)
            correct_answer = question_data['correct_answer'].strip()
            if correct_answer in ['A', 'B', 'C', 'D']:
                answer_index = ord(correct_answer) - ord('A')
                if 0 <= answer_index < len(question_data['options']):
                    correct_answer = question_data['options'][answer_index]
                else:
                    print(f"Invalid answer index for topic {topic['name']}: {correct_answer}")
                    return None
            
            # Create and save the question to the database
            new_question = Question(
                topic_id=topic['id'],
                content=question_data['question'],
                question_type='multiple_choice',
                options=question_data['options'],
                correct_answer=correct_answer,  # Use the converted answer
                explanation=question_data['explanation'],
                difficulty=target_difficulty
            )
            
            db.add(new_question)
            await db.commit()
            await db.refresh(new_question)
            
            print(f"Successfully created new question {new_question.id} for topic {topic['name']}")
            
            # Return the question data in the expected format
            return {
                'question_id': new_question.id,
                'question': new_question.content,
                'options': new_question.options,
                'difficulty': new_question.difficulty,
                'topic_id': topic['id'],
                'topic_name': topic['name'],
                'selection_strategy': 'generated',
                'topic_ucb_score': topic.get('ucb_score', 0),
                'topic_interest_score': topic.get('interest_score', 0.5),
                'is_generated': True
            }
            
        except Exception as e:
            print(f"Error generating question for topic {topic['name']}: {str(e)}")
            return None


# Global instance
adaptive_question_selector = AdaptiveQuestionSelector()