"""
Dynamic Topic Generator - Uses Gemini to create new subtopics on-demand
"""
import json
import re
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Topic, UserSkillProgress, UserInterest
from services.gemini_service import GeminiService

class DynamicTopicGenerator:
    def __init__(self):
        self.gemini_service = GeminiService()
    
    async def generate_subtopics(
        self, 
        db: AsyncSession, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        count: int = 3
    ) -> List[Dict]:
        """
        Generate new subtopics for a parent topic based on user interests and proficiency
        """
        # Get user's interest level for this topic
        interest_score = await self._get_user_interest_score(db, parent_topic.id, user_interests)
        
        # Generate prompt based on parent topic and user interests
        prompt = self._create_generation_prompt(parent_topic, user_interests, interest_score, count)
        
        try:
            # Get AI response
            response = await self.gemini_service.generate_content(prompt)
            
            # Parse and validate the response
            subtopics = self._parse_subtopics_response(response, parent_topic)
            
            return subtopics[:count]  # Limit to requested count
            
        except Exception as e:
            print(f"Error generating subtopics: {e}")
            # Fallback to basic subtopics if AI fails
            return self._create_fallback_subtopics(parent_topic, count)
    
    def _create_generation_prompt(
        self, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        interest_score: float, 
        count: int
    ) -> str:
        """Create a prompt for Gemini to generate subtopics"""
        
        # Build interest context
        high_interest_topics = [
            interest['topic_name'] for interest in user_interests 
            if interest.get('interest_score', 0) > 0.6
        ]
        
        interest_context = ""
        if high_interest_topics:
            interest_context = f"\n\nThe user has shown high interest in: {', '.join(high_interest_topics)}. Consider this when generating subtopics."
        
        # Determine difficulty based on interest and current topic depth
        difficulty_guidance = self._get_difficulty_guidance(parent_topic, interest_score)
        
        # Create high-level categories that organize the field, not specific techniques
        depth_guidance = """
Create HIGH-LEVEL CATEGORIES that organize this field into major conceptual areas, such as:
- Core fundamentals and theory
- Key methodologies and approaches
- Applications and use cases  
- Analysis and evaluation
- Advanced topics and research frontiers

AVOID overly specific techniques, algorithms, or narrow applications.
Think like organizing a textbook's main chapters, not individual sections or techniques."""

        prompt = f"""You are subdividing a topic into its fundamental knowledge domains. Your goal is to create a COMPLETE and NON-OVERLAPPING breakdown.

Topic: "{parent_topic.name}"
Description: "{parent_topic.description}"

CRITICAL REQUIREMENTS:
1. MUTUALLY EXCLUSIVE: Each subtopic covers a distinct area with NO overlap between any subtopics
2. COLLECTIVELY EXHAUSTIVE: Together, the subtopics must cover EVERYTHING in the parent topic
3. KNOWLEDGE-FOCUSED: Generate conceptual divisions and paradigms, NOT methodologies or processes
4. COMPLETE COVERAGE: A student mastering all {count} subtopics should have comprehensive knowledge of "{parent_topic.name}"

METHODOLOGY - Apply MECE Principle:
- Start by identifying ALL major areas within the topic
- Group related concepts into broader categories to avoid overlap
- Ensure no important area is left uncovered
- Test: Can a concept belong to multiple subtopics? If yes, reorganize.

GOOD EXAMPLES (MECE):
- For "Mathematics": Pure Mathematics, Applied Mathematics, Statistics & Probability (non-overlapping domains)
- For "Biology": Molecular Biology, Ecology, Evolution & Genetics, Physiology (distinct scales/approaches)
- For "Computer Science": Theoretical Foundations, Systems & Software, Data & AI, Human-Computer Interaction (orthogonal areas)

BAD EXAMPLES (VIOLATE MECE):
- For "Mathematics": Algebra, Calculus, Problem Solving (Problem Solving uses Algebra & Calculus)
- For "Biology": Genetics, Molecular Biology, DNA (Genetics includes DNA, overlaps with Molecular Biology)
- For "Computer Science": Programming, Software Engineering, Web Development (Web Dev is part of Programming/Software Eng)

VALIDATION CHECKLIST:
✓ Each subtopic addresses a different fundamental question or aspect
✓ No subtopic is a subset, tool, or application of another
✓ Combined subtopics represent 100% of the parent topic's scope
✓ An expert could specialize in one subtopic without deep knowledge of others

Generate {count} subtopics that represent the fundamental knowledge divisions of "{parent_topic.name}".

Return ONLY this JSON:
[
  {{
    "name": "Subdivision Name",
    "description": "What this subdivision covers",
    "difficulty_min": {max(1, parent_topic.difficulty_min)},
    "difficulty_max": {min(10, parent_topic.difficulty_max + 1)},
    "learning_objectives": ["Learn core concepts", "Understand principles", "Apply knowledge"]
  }}
]"""

        return prompt
    
    def _get_difficulty_guidance(self, parent_topic: Topic, interest_score: float) -> str:
        """Generate difficulty guidance based on topic depth and interest"""
        if interest_score > 0.7:
            return "The user shows high interest, so include some advanced/specialized subtopics."
        elif interest_score < 0.3:
            return "The user shows low interest, so focus on foundational/practical subtopics."
        else:
            return "Balance foundational concepts with some intermediate topics."
    
    async def _get_user_interest_score(
        self, 
        db: AsyncSession, 
        topic_id: int, 
        user_interests: List[Dict]
    ) -> float:
        """Get user's interest score for a specific topic"""
        for interest in user_interests:
            if interest.get('topic_id') == topic_id:
                return interest.get('interest_score', 0.5)
        return 0.5  # Default neutral interest
    
    def _parse_subtopics_response(self, response: str, parent_topic: Topic) -> List[Dict]:
        """Parse and validate Gemini's response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in response")
            
            json_str = json_match.group(0)
            
            # Clean up unicode quotes and other formatting issues
            json_str = json_str.replace('"', '"').replace('"', '"')  # Fix curly quotes
            json_str = json_str.replace(''', "'").replace(''', "'")  # Fix curly apostrophes
            json_str = json_str.replace('…', '...')  # Fix ellipsis
            json_str = json_str.replace('—', '-').replace('–', '-')  # Fix dashes
            json_str = json_str.replace('\u201c', '"').replace('\u201d', '"')  # Unicode quotes
            json_str = json_str.replace('\u2018', "'").replace('\u2019', "'")  # Unicode apostrophes
            json_str = json_str.replace('\u2026', '...')  # Unicode ellipsis
            
            subtopics = json.loads(json_str)
            
            if not isinstance(subtopics, list):
                raise ValueError("Response is not a list")
            
            # Validate and clean each subtopic
            validated_subtopics = []
            for subtopic in subtopics:
                validated = self._validate_subtopic(subtopic, parent_topic)
                if validated:
                    validated_subtopics.append(validated)
            
            return validated_subtopics
            
        except Exception as e:
            print(f"Error parsing subtopics response: {e}")
            print(f"Response was: {response}")
            raise
    
    def _validate_subtopic(self, subtopic: Dict, parent_topic: Topic) -> Optional[Dict]:
        """Validate and clean a single subtopic"""
        try:
            # Required fields
            name = subtopic.get('name', '').strip()
            description = subtopic.get('description', '').strip()
            
            if not name or not description:
                return None
            
            # Ensure name is reasonable length
            if len(name) > 100:
                name = name[:97] + "..."
            
            # Ensure description is reasonable length
            if len(description) > 500:
                description = description[:497] + "..."
            
            # Validate difficulty
            difficulty_min = max(1, min(10, int(subtopic.get('difficulty_min', parent_topic.difficulty_min))))
            difficulty_max = max(difficulty_min, min(10, int(subtopic.get('difficulty_max', parent_topic.difficulty_max + 1))))
            
            # Ensure difficulty progression
            difficulty_min = max(difficulty_min, parent_topic.difficulty_min)
            difficulty_max = min(difficulty_max, parent_topic.difficulty_max + 2)
            
            return {
                "name": name,
                "description": description,
                "difficulty_min": difficulty_min,
                "difficulty_max": difficulty_max,
                "learning_objectives": subtopic.get('learning_objectives', [])
            }
            
        except Exception as e:
            print(f"Error validating subtopic: {e}")
            return None
    
    def _create_fallback_subtopics(self, parent_topic: Topic, count: int) -> List[Dict]:
        """Create basic fallback subtopics if AI generation fails"""
        base_name = parent_topic.name
        
        fallback_subtopics = []
        
        # Special case for root "Artificial Intelligence" topic - use major AI domains
        if base_name == "Artificial Intelligence":
            major_ai_domains = [
                {
                    "name": "Machine Learning",
                    "description": "Algorithms that improve automatically through experience and data",
                    "difficulty_min": 2,
                    "difficulty_max": 8
                },
                {
                    "name": "Computer Vision", 
                    "description": "Enabling computers to interpret and understand visual information",
                    "difficulty_min": 4,
                    "difficulty_max": 9
                },
                {
                    "name": "Natural Language Processing",
                    "description": "Teaching machines to understand, interpret and generate human language", 
                    "difficulty_min": 3,
                    "difficulty_max": 8
                },
                {
                    "name": "Deep Learning",
                    "description": "Neural networks with multiple layers for complex pattern recognition",
                    "difficulty_min": 4,
                    "difficulty_max": 9
                },
                {
                    "name": "Reinforcement Learning",
                    "description": "Learning optimal actions through trial-and-error with environmental feedback",
                    "difficulty_min": 5,
                    "difficulty_max": 9
                },
                {
                    "name": "AI Ethics and Safety",
                    "description": "Responsible development and deployment of artificial intelligence systems",
                    "difficulty_min": 2,
                    "difficulty_max": 6
                },
                {
                    "name": "Robotics and AI",
                    "description": "Integration of AI with robotic systems for autonomous behavior",
                    "difficulty_min": 5,
                    "difficulty_max": 9
                }
            ]
            
            # Return all major domains, not limited by count for the root topic
            for domain in major_ai_domains:
                domain["learning_objectives"] = [
                    f"Understand core principles of {domain['name'].lower()}",
                    f"Learn key techniques and methodologies",
                    f"Apply concepts to real-world problems"
                ]
            
            return major_ai_domains
        else:
            # Generic subtopic patterns for non-root topics
            patterns = [
                f"Fundamentals of {base_name}",
                f"Advanced {base_name}",
                f"Applications of {base_name}",
                f"{base_name} Algorithms",
                f"{base_name} Best Practices",
                f"{base_name} Case Studies",
                f"Modern {base_name}",
                f"{base_name} Tools and Techniques"
            ]
            
            for i in range(min(count, len(patterns))):
                fallback_subtopics.append({
                    "name": patterns[i],
                    "description": f"Explore key concepts and techniques in {patterns[i].lower()}",
                    "difficulty_min": parent_topic.difficulty_min,
                    "difficulty_max": min(10, parent_topic.difficulty_max + 1),
                    "learning_objectives": [
                        f"Understand core concepts of {patterns[i].lower()}",
                        f"Apply techniques in practical scenarios",
                        f"Analyze real-world examples"
                    ]
                })
            
            return fallback_subtopics
    
    async def create_topics_in_database(
        self, 
        db: AsyncSession, 
        subtopics_data: List[Dict], 
        parent_id: int
    ) -> List[Topic]:
        """Create the generated subtopics in the database"""
        created_topics = []
        
        for subtopic_data in subtopics_data:
            # Check if topic already exists
            existing = await db.execute(
                select(Topic).where(
                    Topic.name == subtopic_data['name'],
                    Topic.parent_id == parent_id
                )
            )
            
            if existing.scalar_one_or_none():
                continue  # Skip if already exists
            
            # Create new topic
            topic = Topic(
                name=subtopic_data['name'],
                description=subtopic_data['description'],
                parent_id=parent_id,
                difficulty_min=subtopic_data['difficulty_min'],
                difficulty_max=subtopic_data['difficulty_max']
            )
            
            db.add(topic)
            await db.flush()  # Get the ID
            created_topics.append(topic)
            
            print(f"✨ Generated new topic: {topic.name} (ID: {topic.id})")
        
        return created_topics