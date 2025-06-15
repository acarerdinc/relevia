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
from services.mece_validator import mece_validator
from core.logging_config import logger

# Create specialized logger for subtopic generation
subtopic_logger = logger.getChild("subtopic_generation")

class DynamicTopicGenerator:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.max_tree_depth = 5  # Limit tree depth to prevent over-specialization
        self.max_siblings_per_parent = 12  # Reasonable limit for subtopics
    
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
        
        # Check tree depth to prevent over-specialization
        current_depth = await self._get_topic_depth(db, parent_topic)
        if current_depth >= self.max_tree_depth:
            subtopic_logger.warning(f"⚠️ [GEN:{generation_id}] Maximum tree depth ({self.max_tree_depth}) reached. Skipping generation.")
            return []
        
        # Get user's interest level for this topic
        subtopic_logger.info(f"🔍 [GEN:{generation_id}] Getting user interest score...")
        interest_score = await self._get_user_interest_score(db, parent_topic.id, user_interests)
        subtopic_logger.info(f"📈 [GEN:{generation_id}] Interest score: {interest_score}")
        
        # Generate prompt based on parent topic and user interests (count=None means AI determines optimal number)
        prompt = self._create_generation_prompt(parent_topic, user_interests, interest_score, count, current_depth)
        
        try:
            # Get AI response
            response = await self.gemini_service.generate_content(prompt)
            
            # Parse and validate the response
            subtopics = self._parse_subtopics_response(response, parent_topic)
            
            if not subtopics:
                print(f"❌ AI generation failed for {parent_topic.name} - no valid subtopics generated")
                return []
            
            # Validate MECE principles with enhanced validator
            cleaned_subtopics, violations = await mece_validator.validate_and_clean_subtopics(
                subtopics, parent_topic, auto_fix=True
            )
            
            if violations:
                subtopic_logger.warning(f"⚠️ MECE violations found and fixed: {len(violations)} issues")
                for v in violations[:3]:  # Log first 3 violations
                    subtopic_logger.info(f"  - {v}")
            
            # Run basic validation on cleaned subtopics
            if not self._validate_mece_principles(cleaned_subtopics, parent_topic):
                subtopic_logger.error(f"❌ Cleaned subtopics still violate MECE principles")
                return []
            
            subtopics = cleaned_subtopics
            
            print(f"✅ Generated {len(subtopics)} MECE-compliant subtopics for {parent_topic.name}")
            return subtopics
            
        except Exception as e:
            subtopic_logger.error(f"💥 [GEN:{generation_id}] Failed to generate subtopics: {str(e)}")
            subtopic_logger.error(f"📚 [GEN:{generation_id}] Stack trace:\n{traceback.format_exc()}")
            
            # Fallback generation when AI is not available
            if "Gemini model not initialized" in str(e) or "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
                subtopic_logger.error(f"🚨 [GEN:{generation_id}] GEMINI API ISSUE: {str(e)}")
                print(f"🚨 CRITICAL: Gemini API failed - {str(e)}")
                print(f"🔧 Please check your GEMINI_API_KEY in .env file")
                print(f"🌐 Get a valid key from: https://aistudio.google.com/apikey")
                print(f"⚠️ Using empty fallback (no hardcoded topics)")
                # Get existing children to inform fallback selection
                existing_children = await db.execute(select(Topic).where(Topic.parent_id == parent_topic.id))
                existing_names = {child.name for child in existing_children.scalars().all()}
                return self._generate_fallback_subtopics(parent_topic, user_interests, count, existing_names)
            
            return []
    
    def _generate_fallback_subtopics(self, parent_topic: Topic, user_interests: List[UserInterest], count: Optional[int] = None, existing_names: set = None) -> List[Dict]:
        """Generate simple fallback subtopics when AI is unavailable - NO HARDCODING"""
        
        if existing_names is None:
            existing_names = set()
        
        # When AI is not available, return empty list instead of hardcoded topics
        # This forces the system to work with existing topics only
        subtopic_logger.warning(f"⚠️ AI unavailable - no fallback subtopics generated for {parent_topic.name}")
        return []
    
    def _create_generation_prompt(
        self, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        interest_score: float, 
        count: int = None,
        current_depth: int = 0
    ) -> str:
        """Create a comprehensive prompt for Gemini to generate subtopics using MECE principles"""
        
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
        
        # Depth-aware guidance to maintain consistent abstraction levels
        depth_guidance = self._get_depth_guidance(current_depth)
        
        # Determine appropriate number of subtopics based on depth
        if count is None:
            if current_depth <= 1:
                count_guidance = "Generate 3-7 major subdivisions that completely cover the topic."
            elif current_depth <= 3:
                count_guidance = "Generate 3-6 focused subdivisions."
            else:
                count_guidance = "Generate 2-4 specific subdivisions only if absolutely necessary."
        else:
            count_guidance = f"Generate exactly {count} subdivisions."

        prompt = f"""You are subdividing a topic into its fundamental knowledge domains. Your goal is to create a COMPLETE and NON-OVERLAPPING breakdown.

Topic: "{parent_topic.name}"
Description: "{parent_topic.description}"
Tree Depth: Level {current_depth + 1} (Root = 0)

{depth_guidance}

CRITICAL REQUIREMENTS:
1. MUTUALLY EXCLUSIVE: Each subtopic covers a distinct area with NO overlap between any subtopics
2. COLLECTIVELY EXHAUSTIVE: Together, the subtopics must cover EVERYTHING in the parent topic
3. NO DUPLICATES: Each subtopic name must be unique - no repeating names
4. NO SUBSETS: No subtopic should be a subset or special case of another sibling
5. CONSISTENT ABSTRACTION: All subtopics at the same level should have similar levels of specificity

MECE VALIDATION RULES:
- Before finalizing, check every pair of subtopics for overlap
- If two subtopics share >50% conceptual overlap, merge them
- If one subtopic is entirely contained within another, remove or restructure
- Ensure naming is distinct - avoid using the same key terms across siblings

EXAMPLES OF VIOLATIONS TO AVOID:
- "Machine Learning" and "Deep Learning" as siblings (Deep Learning ⊂ Machine Learning)
- "Neural Networks" and "Neural Network Architectures" as siblings (redundant)
- "Computer Vision" and "Computer Vision Applications" as siblings (one contains the other)
- Having both generic "Applications" and specific application areas as siblings

{count_guidance}

POST-GENERATION CHECKLIST:
✓ No two subtopics have names that differ by only one word
✓ No subtopic name contains another subtopic's name
✓ Each subtopic addresses a fundamentally different aspect
✓ Combined coverage = 100% of parent topic
✓ An expert in one subtopic doesn't necessarily need deep knowledge of others

Return ONLY this JSON:
[
  {{
    "name": "Unique Subdivision Name",
    "description": "Clear description of what this uniquely covers",
    "difficulty_min": {max(1, parent_topic.difficulty_min)},
    "difficulty_max": {min(10, parent_topic.difficulty_max + 1)},
    "learning_objectives": ["Specific objective 1", "Specific objective 2", "Specific objective 3"]
  }}
]"""

        return prompt
    
    def _get_depth_guidance(self, depth: int) -> str:
        """Get generation guidance based on tree depth"""
        if depth == 0:
            return """
DEPTH GUIDANCE (Root Level):
You are creating the MAJOR BRANCHES of this field. Think of the highest-level divisions that organize 
all knowledge in this domain. These should be broad conceptual categories that could each be a 
separate course or textbook.
"""
        elif depth == 1:
            return """
DEPTH GUIDANCE (Level 1):
You are subdividing a major branch. Create the primary subdivisions that organize this branch into 
its main components. Think of chapter-level divisions in a textbook about this specific branch.
"""
        elif depth == 2:
            return """
DEPTH GUIDANCE (Level 2):
You are creating focused areas within a subdivision. These should be specific enough to guide learning 
but broad enough to contain multiple concepts. Think section-level divisions within a chapter.
"""
        elif depth == 3:
            return """
DEPTH GUIDANCE (Level 3):
You are approaching maximum specificity. Only create subdivisions if they represent fundamentally 
different approaches or paradigms. Avoid creating topics that are just examples or applications.
"""
        else:
            return """
DEPTH GUIDANCE (Deep Level):
You are at maximum depth. Only subdivide if absolutely critical for organizing genuinely distinct 
concepts that cannot be learned together. Most topics at this level should NOT be further subdivided.
"""
    
    def _get_difficulty_guidance(self, parent_topic: Topic, interest_score: float) -> str:
        """Generate difficulty guidance based on topic depth and interest"""
        if interest_score > 0.7:
            return "The user shows high interest, so include some advanced/specialized subtopics."
        elif interest_score < 0.3:
            return "The user shows low interest, so focus on foundational/practical subtopics."
        else:
            return "Balance foundational concepts with some intermediate topics."
    
    async def _get_topic_depth(self, db: AsyncSession, topic: Topic) -> int:
        """Calculate the depth of a topic in the tree"""
        depth = 0
        current_topic = topic
        
        while current_topic.parent_id:
            depth += 1
            if depth > self.max_tree_depth:  # Prevent infinite loops
                break
            
            result = await db.execute(
                select(Topic).where(Topic.id == current_topic.parent_id)
            )
            parent = result.scalar_one_or_none()
            if not parent:
                break
            current_topic = parent
        
        return depth
    
    def _create_generation_prompt(
        self, 
        parent_topic: Topic, 
        user_interests: List[Dict], 
        interest_score: float, 
        count: int = None,
        current_depth: int = 0
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
        
        # Depth-aware guidance to maintain consistent abstraction levels
        depth_guidance = self._get_depth_guidance(current_depth)
        
        # Determine appropriate number of subtopics based on depth
        if count is None:
            if current_depth <= 1:
                count_guidance = "Generate 3-7 major subdivisions that completely cover the topic."
            elif current_depth <= 3:
                count_guidance = "Generate 3-6 focused subdivisions."
            else:
                count_guidance = "Generate 2-4 specific subdivisions only if absolutely necessary."
        else:
            count_guidance = f"Generate exactly {count} subdivisions."

        prompt = f"""You are subdividing a topic into its fundamental knowledge domains. Your goal is to create a COMPLETE and NON-OVERLAPPING breakdown.

Topic: "{parent_topic.name}"
Description: "{parent_topic.description}"
Tree Depth: Level {current_depth + 1} (Root = 0)

{depth_guidance}

CRITICAL REQUIREMENTS:
1. MUTUALLY EXCLUSIVE: Each subtopic covers a distinct area with NO overlap between any subtopics
2. COLLECTIVELY EXHAUSTIVE: Together, the subtopics must cover EVERYTHING in the parent topic
3. NO DUPLICATES: Each subtopic name must be unique - no repeating names
4. NO SUBSETS: No subtopic should be a subset or special case of another sibling
5. CONSISTENT ABSTRACTION: All subtopics at the same level should have similar levels of specificity

MECE VALIDATION RULES:
- Before finalizing, check every pair of subtopics for overlap
- If two subtopics share >50% conceptual overlap, merge them
- If one subtopic is entirely contained within another, remove or restructure
- Ensure naming is distinct - avoid using the same key terms across siblings

EXAMPLES OF VIOLATIONS TO AVOID:
- "Machine Learning" and "Deep Learning" as siblings (Deep Learning ⊂ Machine Learning)
- "Neural Networks" and "Neural Network Architectures" as siblings (redundant)
- "Computer Vision" and "Computer Vision Applications" as siblings (one contains the other)
- Having both generic "Applications" and specific application areas as siblings

{count_guidance}

POST-GENERATION CHECKLIST:
✓ No two subtopics have names that differ by only one word
✓ No subtopic name contains another subtopic's name
✓ Each subtopic addresses a fundamentally different aspect
✓ Combined coverage = 100% of parent topic
✓ An expert in one subtopic doesn't necessarily need deep knowledge of others

Return ONLY this JSON:
[
  {{
    "name": "Unique Subdivision Name",
    "description": "Clear description of what this uniquely covers",
    "difficulty_min": {max(1, parent_topic.difficulty_min)},
    "difficulty_max": {min(10, parent_topic.difficulty_max + 1)},
    "learning_objectives": ["Specific objective 1", "Specific objective 2", "Specific objective 3"]
  }}
]"""

        return prompt
    
    def _get_depth_guidance(self, depth: int) -> str:
        """Get generation guidance based on tree depth"""
        if depth == 0:
            return """
DEPTH GUIDANCE (Root Level):
You are creating the MAJOR BRANCHES of this field. Think of the highest-level divisions that organize 
all knowledge in this domain. These should be broad conceptual categories that could each be a 
separate course or textbook.
"""
        elif depth == 1:
            return """
DEPTH GUIDANCE (Level 1):
You are subdividing a major branch. Create the primary subdivisions that organize this branch into 
its main components. Think of chapter-level divisions in a textbook about this specific branch.
"""
        elif depth == 2:
            return """
DEPTH GUIDANCE (Level 2):
You are creating focused areas within a subdivision. These should be specific enough to guide learning 
but broad enough to contain multiple concepts. Think section-level divisions within a chapter.
"""
        elif depth == 3:
            return """
DEPTH GUIDANCE (Level 3):
You are approaching maximum specificity. Only create subdivisions if they represent fundamentally 
different approaches or paradigms. Avoid creating topics that are just examples or applications.
"""
        else:
            return """
DEPTH GUIDANCE (Deep Level):
You are at maximum depth. Only subdivide if absolutely critical for organizing genuinely distinct 
concepts that cannot be learned together. Most topics at this level should NOT be further subdivided.
"""
    
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
            # Fix smart quotes that might be causing issues
            json_str = json_str.replace('"', '"').replace('"', '"')  # Additional smart quotes
            json_str = json_str.replace(''', "'").replace(''', "'")  # Additional smart apostrophes
            
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
        """Enhanced MECE validation with stricter rules"""
        
        if len(subtopics) < 2:
            subtopic_logger.warning(f"⚠️ MECE: Only {len(subtopics)} subtopics generated - likely not comprehensive")
            return False
        
        if len(subtopics) > self.max_siblings_per_parent:
            subtopic_logger.warning(f"⚠️ MECE: Too many subtopics ({len(subtopics)}) - likely too granular")
            return False
        
        # Check for obvious overlaps in names
        topic_names = [s['name'].lower() for s in subtopics]
        parent_name_lower = parent_topic.name.lower()
        
        # Enhanced duplicate detection
        seen_names = set()
        for name in topic_names:
            if name in seen_names:
                subtopic_logger.error(f"❌ MECE: Exact duplicate found: '{name}'")
                return False
            seen_names.add(name)
        
        # Check for subset relationships in names
        for i, name1 in enumerate(topic_names):
            for j, name2 in enumerate(topic_names):
                if i != j:
                    # One name contains the other
                    if name1 in name2 or name2 in name1:
                        subtopic_logger.warning(f"⚠️ MECE: Subset relationship: '{name1}' and '{name2}'")
                        return False
                    
                    # Names differ by only one word
                    words1 = set(name1.split())
                    words2 = set(name2.split())
                    if len(words1) == len(words2) and len(words1 - words2) == 1:
                        subtopic_logger.warning(f"⚠️ MECE: Too similar: '{name1}' and '{name2}'")
                        return False
        
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
            # Check for exact matches or substring matches
            match_0 = any(pair[0] in name for name in topic_names)
            match_1 = any(pair[1] in name for name in topic_names)
            
            if match_0 and match_1:
                matching_names = [name for name in topic_names if pair[0] in name or pair[1] in name]
                print(f"⚠️ MECE violation detected: '{pair[0]}' and '{pair[1]}' overlap in topics: {matching_names}")
                return False
        
        # Check for duplicate or very similar names
        for i, name1 in enumerate(topic_names):
            for j, name2 in enumerate(topic_names[i+1:], i+1):
                # Check for exact duplicates
                if name1 == name2:
                    print(f"⚠️ Duplicate topic names: '{name1}'")
                    return False
                
                # Check for high word overlap (>60% is too similar for siblings)
                words1 = set(name1.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
                words2 = set(name2.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
                if words1 and words2:  # Avoid division by zero
                    overlap_ratio = len(words1 & words2) / min(len(words1), len(words2))
                    if overlap_ratio > 0.6:
                        subtopic_logger.warning(f"⚠️ MECE: High word overlap ({overlap_ratio:.0%}): '{name1}' and '{name2}'")
                        return False
        
        # Check for "generic + specific" pattern violations
        generic_terms = ['applications', 'techniques', 'methods', 'approaches', 'systems', 'models']
        for term in generic_terms:
            has_generic = any(term in name and len(name.split()) <= 3 for name in topic_names)
            has_specific = any(term in name and len(name.split()) > 3 for name in topic_names)
            
            if has_generic and has_specific:
                subtopic_logger.warning(f"⚠️ MECE: Both generic and specific '{term}' topics present")
                return False
        
        subtopic_logger.info(f"✅ MECE validation passed for {len(subtopics)} subtopics")
        subtopic_logger.debug(f"MECE: Validated topics: {[s['name'] for s in subtopics]}")
        return True
    
    async def create_topics_in_database(
        self, 
        db: AsyncSession, 
        subtopics_data: List[Dict], 
        parent_id: int
    ) -> List[Topic]:
        """Create the generated subtopics in the database"""
        subtopic_logger.info(f"💾 [DB] Starting database creation for {len(subtopics_data)} subtopics under parent_id={parent_id}")
        
        # Get parent topic for final validation
        parent_result = await db.execute(select(Topic).where(Topic.id == parent_id))
        parent_topic = parent_result.scalar_one_or_none()
        
        if parent_topic:
            # Final MECE validation before database insertion
            cleaned_data, violations = await mece_validator.validate_and_clean_subtopics(
                subtopics_data, parent_topic, auto_fix=True
            )
            if violations:
                subtopic_logger.info(f"📝 [DB] Pre-insertion cleanup: {len(violations)} issues fixed")
            subtopics_data = cleaned_data
        
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