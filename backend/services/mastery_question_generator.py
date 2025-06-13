"""
Mastery Question Generator - Creates questions tailored to specific mastery levels
"""

from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Topic, Question
from services.gemini_service import GeminiService
from core.mastery_levels import MasteryLevel, MASTERY_DESCRIPTIONS
import json
import re

class MasteryQuestionGenerator:
    """Generates questions specific to mastery levels"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
    
    async def generate_mastery_question(
        self, 
        db: AsyncSession, 
        topic: Topic, 
        mastery_level: MasteryLevel,
        existing_questions: List[str] = None
    ) -> Dict:
        """Generate a single question for specific mastery level"""
        
        if existing_questions is None:
            existing_questions = []
        
        prompt = self._create_mastery_prompt(topic, mastery_level, existing_questions)
        
        try:
            response = await self.gemini_service.generate_content(prompt)
            question_data = self._parse_question_response(response, mastery_level)
            return question_data
            
        except Exception as e:
            print(f"Error generating mastery question: {e}")
            return self._create_fallback_question(topic, mastery_level)
    
    def _create_mastery_prompt(self, topic: Topic, mastery_level: MasteryLevel, existing_questions: List[str]) -> str:
        """Create mastery-level specific prompt"""
        
        mastery_info = MASTERY_DESCRIPTIONS[mastery_level]
        
        # Get mastery-specific requirements
        level_requirements = self._get_level_requirements(mastery_level)
        
        existing_context = ""
        if existing_questions:
            existing_context = f"""
AVOID repeating these existing questions:
{chr(10).join(f"- {q}" for q in existing_questions[-5:])}
"""

        prompt = f"""You are creating a {mastery_info['title']} level question for "{topic.name}".

Topic: {topic.name}
Description: {topic.description}
Mastery Level: {mastery_info['title']} ({mastery_info['equivalent']})
Target: {mastery_info['description']}

{level_requirements}

{existing_context}

Generate exactly ONE high-quality question that tests {mastery_level} level understanding.

Return ONLY this JSON:
{{
    "question": "The question text",
    "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
    "correct_answer": "A",
    "explanation": "Detailed explanation of why this answer is correct and others are wrong",
    "difficulty": {self._get_difficulty_for_level(mastery_level)}
}}"""

        return prompt
    
    def _get_level_requirements(self, mastery_level: MasteryLevel) -> str:
        """Get specific requirements for each mastery level"""
        
        requirements = {
            MasteryLevel.NOVICE: """
NOVICE LEVEL REQUIREMENTS:
- Test basic definitions and fundamental concepts
- Focus on recognition and recall
- Use clear, straightforward language
- Test essential vocabulary and basic principles
- Avoid complex scenarios or edge cases
- Example: "What is machine learning?" or "Which of these is a supervised learning algorithm?"
""",
            MasteryLevel.COMPETENT: """
COMPETENT LEVEL REQUIREMENTS:
- Test application of concepts to common scenarios
- Require understanding of relationships between concepts
- Include practical problem-solving
- Test ability to categorize and compare approaches
- Example: "Which algorithm would be best for this classification problem?" or "What preprocessing step is needed here?"
""",
            MasteryLevel.PROFICIENT: """
PROFICIENT LEVEL REQUIREMENTS:
- Test analysis and synthesis of complex scenarios
- Require deep understanding of trade-offs and limitations
- Include multi-step reasoning
- Test ability to evaluate and critique approaches
- Example: "Analyze why this model failed and what could improve it" or "Compare the theoretical foundations of these approaches"
""",
            MasteryLevel.EXPERT: """
EXPERT LEVEL REQUIREMENTS:
- Test advanced edge cases and nuanced understanding
- Require knowledge of cutting-edge developments
- Include complex real-world scenarios
- Test ability to design novel solutions
- Example: "How would you handle this complex optimization constraint?" or "What are the implications of this recent research finding?"
""",
            MasteryLevel.MASTER: """
MASTER LEVEL REQUIREMENTS:
- Test research-level understanding and innovation
- Require knowledge of open problems and current frontiers
- Include theoretical depth and mathematical rigor
- Test ability to push boundaries of current knowledge
- Example: "Propose a novel approach to this unsolved problem" or "Critique this cutting-edge research methodology"
"""
        }
        
        return requirements.get(mastery_level, requirements[MasteryLevel.NOVICE])
    
    def _get_difficulty_for_level(self, mastery_level: MasteryLevel) -> int:
        """Map mastery level to difficulty score"""
        difficulty_mapping = {
            MasteryLevel.NOVICE: 2,
            MasteryLevel.COMPETENT: 4,
            MasteryLevel.PROFICIENT: 6,
            MasteryLevel.EXPERT: 8,
            MasteryLevel.MASTER: 10
        }
        return difficulty_mapping.get(mastery_level, 2)
    
    def _parse_question_response(self, response: str, mastery_level: MasteryLevel) -> Dict:
        """Parse Gemini response into question data"""
        try:
            # Extract JSON from response, handling code blocks
            if response.strip().startswith('```'):
                # Remove code blocks
                lines = response.strip().split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_json = not in_json
                        continue
                    if in_json:
                        json_lines.append(line)
                json_str = '\n'.join(json_lines)
            else:
                json_str = response.strip()
            
            # Try to parse the cleaned JSON directly
            question_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['question', 'options', 'correct_answer', 'explanation']
            for field in required_fields:
                if field not in question_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Add mastery level and ensure difficulty
            question_data['mastery_level'] = mastery_level
            question_data['difficulty'] = question_data.get('difficulty', self._get_difficulty_for_level(mastery_level))
            
            return question_data
            
        except Exception as e:
            print(f"Error parsing question response: {e}")
            print(f"Response was: {response}")
            raise
    
    def _create_fallback_question(self, topic: Topic, mastery_level: MasteryLevel) -> Dict:
        """Create a fallback question if generation fails"""
        return {
            "question": f"What is a key concept in {topic.name}?",
            "options": [
                "A) First concept",
                "B) Second concept", 
                "C) Third concept",
                "D) Fourth concept"
            ],
            "correct_answer": "A",
            "explanation": f"This is a basic question about {topic.name} at {mastery_level} level.",
            "difficulty": self._get_difficulty_for_level(mastery_level),
            "mastery_level": mastery_level
        }
    
    async def generate_question_batch(
        self, 
        db: AsyncSession, 
        topic: Topic, 
        mastery_level: MasteryLevel, 
        count: int = 5
    ) -> List[Dict]:
        """Generate a batch of questions for a mastery level"""
        questions = []
        existing_questions = []
        
        for i in range(count):
            try:
                question_data = await self.generate_mastery_question(
                    db, topic, mastery_level, existing_questions
                )
                questions.append(question_data)
                existing_questions.append(question_data['question'])
                
            except Exception as e:
                print(f"Failed to generate question {i+1}: {e}")
                # Continue with fallback
                fallback = self._create_fallback_question(topic, mastery_level)
                questions.append(fallback)
        
        return questions