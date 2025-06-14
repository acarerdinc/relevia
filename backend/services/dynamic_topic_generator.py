"""
Dynamic Topic Generator - Uses Gemini to create new subtopics on-demand
"""
import json
import re
import time
import traceback
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Topic, UserSkillProgress, UserInterest
from services.gemini_service import GeminiService
from core.logging_config import logger

# Create specialized logger for subtopic generation
subtopic_logger = logger.getChild("subtopic_generation")

class DynamicTopicGenerator:
    def __init__(self):
        self.gemini_service = GeminiService()
    
    async def generate_subtopics(
        self, 
        db: AsyncSession, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        count: int = None
    ) -> List[Dict]:
        """
        Generate new subtopics for a parent topic based on user interests and proficiency
        """
        generation_id = f"{parent_topic.name}_{int(time.time())}"
        subtopic_logger.info(f"🚀 [GEN:{generation_id}] Starting subtopic generation for '{parent_topic.name}' (ID: {parent_topic.id})")
        subtopic_logger.info(f"📊 [GEN:{generation_id}] User interests count: {len(user_interests)}, Requested count: {count}")
        
        # Get user's interest level for this topic
        subtopic_logger.info(f"🔍 [GEN:{generation_id}] Getting user interest score...")
        interest_score = await self._get_user_interest_score(db, parent_topic.id, user_interests)
        subtopic_logger.info(f"📈 [GEN:{generation_id}] Interest score: {interest_score}")
        
        # Generate prompt based on parent topic and user interests (count=None means AI determines optimal number)
        prompt = self._create_generation_prompt(parent_topic, user_interests, interest_score, count)
        
        try:
            # Get AI response
            response = await self.gemini_service.generate_content(prompt)
            
            # Parse and validate the response
            subtopics = self._parse_subtopics_response(response, parent_topic)
            
            if not subtopics:
                print(f"❌ AI generation failed for {parent_topic.name} - no valid subtopics generated")
                return []
            
            # Validate MECE principles
            if not self._validate_mece_principles(subtopics, parent_topic):
                print(f"⚠️ Generated subtopics for {parent_topic.name} violate MECE principles - retrying with stronger instructions")
                # TODO: Could add retry logic here
                return []
            
            print(f"✅ Generated {len(subtopics)} MECE-compliant subtopics for {parent_topic.name}")
            return subtopics
            
        except Exception as e:
            subtopic_logger.error(f"💥 [GEN:{generation_id}] Failed to generate subtopics: {str(e)}")
            subtopic_logger.error(f"📚 [GEN:{generation_id}] Stack trace:\n{traceback.format_exc()}")
            return []
    
    def _create_generation_prompt(
        self, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        interest_score: float, 
        count: int = None
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
4. COMPLETE COVERAGE: A student mastering all generated subtopics should have comprehensive knowledge of "{parent_topic.name}"

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

Generate AS MANY subtopics as needed to create a complete MECE breakdown of "{parent_topic.name}". 
Do not limit yourself to a fixed number - generate however many subtopics are required for proper coverage.

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
    
    def _validate_mece_principles(self, subtopics: List[Dict], parent_topic: Topic) -> bool:
        """Validate that generated subtopics follow MECE principles"""
        
        if len(subtopics) < 2:
            subtopic_logger.warning(f"⚠️ MECE: Only {len(subtopics)} subtopics generated - likely not comprehensive")
            return False
        
        # Check for obvious overlaps in names
        topic_names = [s['name'].lower() for s in subtopics]
        parent_name_lower = parent_topic.name.lower()
        
        # Known problematic combinations that violate MECE
        # BUT: Don't flag if one of the terms is the parent topic itself
        problematic_pairs = [
            ('computer vision', 'deep learning'),
            ('machine learning', 'deep learning'),
            ('artificial intelligence', 'machine learning'),
            ('programming', 'software engineering'),
            ('algorithms', 'data structures'),
            ('neural networks', 'deep learning'),
            ('supervised learning', 'machine learning'),
            ('web development', 'software engineering'),
            # AI application overlaps
            ('applications of ai', 'ai in'),  # Generic "applications" conflicts with specific "ai in X"
            ('applications of ai', 'business'),
            ('applications of ai', 'autonomous'),
            ('applications of ai', 'healthcare'),
            ('applications of ai', 'finance')
        ]
        
        for pair in problematic_pairs:
            # Skip validation if one of the pair terms is the parent topic
            if pair[0] in parent_name_lower or pair[1] in parent_name_lower:
                continue
                
            # For the remaining pairs, look for actual conceptual overlaps
            # not just keyword presence in different contexts
            topics_with_first = [name for name in topic_names if pair[0] in name]
            topics_with_second = [name for name in topic_names if pair[1] in name]
            
            # Only flag if we have topics that seem to be about the same concept
            if topics_with_first and topics_with_second:
                # Check if any topic names suggest actual overlap
                # e.g., "Deep Learning" and "Deep Learning Applications" would overlap
                # but "Mathematical Foundations of Machine Learning" and "Deep Learning" don't
                for t1 in topics_with_first:
                    for t2 in topics_with_second:
                        # Check for actual conceptual overlap
                        if self._check_conceptual_overlap(t1, t2, pair[0], pair[1]):
                            subtopic_logger.warning(f"⚠️ MECE violation: '{t1}' and '{t2}' have conceptual overlap")
                            subtopic_logger.debug(f"MECE: Problematic pair: {pair}")
                            return False
        
        # Check for duplicate or very similar names
        for i, name1 in enumerate(topic_names):
            for j, name2 in enumerate(topic_names[i+1:], i+1):
                # Check for exact duplicates
                if name1 == name2:
                    subtopic_logger.warning(f"⚠️ MECE: Duplicate topic names: '{name1}'")
                    return False
                
                # Check for very similar names (>80% overlap in words)
                words1 = set(name1.split())
                words2 = set(name2.split())
                if len(words1 & words2) / max(len(words1), len(words2)) > 0.8:
                    print(f"⚠️ Very similar topic names: '{name1}' and '{name2}'")
                    return False
        
        # For AI specifically, ensure comprehensive coverage
        if parent_topic.name == "Artificial Intelligence":
            expected_domains = [
                'machine learning', 'natural language', 'computer vision', 
                'robotics', 'knowledge', 'expert system', 'reasoning', 'ethics'
            ]
            covered_domains = []
            
            for name in topic_names:
                for domain in expected_domains:
                    if domain in name:
                        covered_domains.append(domain)
                        break
            
            coverage_ratio = len(set(covered_domains)) / len(expected_domains)
            if coverage_ratio < 0.4:  # Should cover at least 40% of major AI domains (relaxed)
                print(f"⚠️ AI subtopics only cover {coverage_ratio:.0%} of major domains - not collectively exhaustive")
                return False
        
        subtopic_logger.info(f"✅ MECE validation passed for {len(subtopics)} subtopics")
        subtopic_logger.debug(f"MECE: Validated topics: {[s['name'] for s in subtopics]}")
        return True
    
    def _check_conceptual_overlap(self, topic1: str, topic2: str, term1: str, term2: str) -> bool:
        """Check if two topics have actual conceptual overlap beyond keyword presence"""
        
        # Remove the terms to see what's left
        topic1_core = topic1.replace(term1, '').strip()
        topic2_core = topic2.replace(term2, '').strip()
        
        # If the core concepts are very similar, it's an overlap
        # e.g., "Deep Learning" and "Deep Learning Fundamentals" -> overlap
        # but "Mathematical Foundations of Machine Learning" and "Deep Learning" -> no overlap
        
        # Check for subset relationships
        if topic1_core in topic2 or topic2_core in topic1:
            return True
            
        # Check if one is just a variant of the other
        if topic1_core == topic2_core:
            return True
            
        # Check for common modifiers that indicate same concept
        overlap_indicators = ['fundamentals', 'basics', 'introduction', 'advanced', 'applications']
        for indicator in overlap_indicators:
            if indicator in topic1_core and indicator in topic2_core:
                return True
                
        return False
    
    async def create_topics_in_database(
        self, 
        db: AsyncSession, 
        subtopics_data: List[Dict], 
        parent_id: int
    ) -> List[Topic]:
        """Create the generated subtopics in the database"""
        subtopic_logger.info(f"💾 [DB] Starting database creation for {len(subtopics_data)} subtopics under parent_id={parent_id}")
        created_topics = []
        
        for i, subtopic_data in enumerate(subtopics_data):
            try:
                # Validate required fields
                required_fields = ['name', 'description', 'difficulty_min', 'difficulty_max']
                missing_fields = [f for f in required_fields if f not in subtopic_data]
                if missing_fields:
                    subtopic_logger.error(f"💥 [DB] Subtopic missing required fields: {missing_fields}")
                    subtopic_logger.error(f"💥 [DB] Subtopic data: {subtopic_data}")
                    continue
                    
                subtopic_logger.debug(f"💾 [DB] Processing subtopic {i+1}/{len(subtopics_data)}: {subtopic_data['name']}")
                
                # Check if topic already exists
                subtopic_logger.debug(f"💾 [DB] Checking if '{subtopic_data['name']}' already exists...")
                existing = await db.execute(
                    select(Topic).where(
                        Topic.name == subtopic_data['name'],
                        Topic.parent_id == parent_id
                    )
                )
                subtopic_logger.debug(f"💾 [DB] Existence check completed")
                
                if existing.scalar_one_or_none():
                    subtopic_logger.info(f"⏭️ [DB] Skipping '{subtopic_data['name']}' - already exists")
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
                subtopic_logger.debug(f"💾 [DB] Added '{subtopic_data['name']}' to session")
                
                await db.flush()  # Get the ID
                subtopic_logger.debug(f"✅ [DB] Flushed '{subtopic_data['name']}' - got ID: {topic.id}")
                
                created_topics.append(topic)
            except Exception as e:
                subtopic_logger.error(f"💥 [DB] Failed to create topic '{subtopic_data['name']}': {str(e)}")
                subtopic_logger.error(f"📚 [DB] Stack trace:\n{traceback.format_exc()}")
                # Continue with other topics
                continue
            
            print(f"✨ Generated new topic: {topic.name} (ID: {topic.id})")
        
        subtopic_logger.info(f"✅ [DB] Successfully created {len(created_topics)} topics in database")
        return created_topics