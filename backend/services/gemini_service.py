import google.generativeai as genai
from typing import Dict, List, Optional
from core.config import settings
from core.logging_config import logger
import json

class GeminiService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # Try different model names (corrected model names)
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash')
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-2.0-pro')
                except:
                    try:
                        self.model = genai.GenerativeModel('gemini-pro')
                    except:
                        self.model = None
                        logger.warning("Could not initialize any Gemini model")
        else:
            self.model = None
            logger.warning("Gemini API key not configured. Question generation will use fallback questions")
    
    async def generate_question(
        self, 
        topic: str, 
        difficulty: int, 
        question_type: str = "multiple_choice",
        context: Optional[Dict] = None
    ) -> Dict:
        """Generate a question using Gemini AI"""
        
        prompt = f"""Generate a multiple choice question about {topic} for difficulty level {difficulty}/10.

Context: {json.dumps(context) if context else 'General knowledge'}

Difficulty guidelines:
- 1-3: Basic definitions and concepts
- 4-6: Understanding and application
- 7-9: Advanced analysis and synthesis  
- 10: Expert-level, cutting-edge topics

CRITICAL REQUIREMENT: You MUST provide exactly 4 options, no more, no less.

Respond with ONLY a valid JSON object in this exact format:
{{
  "question": "Clear, specific question about {topic}",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "The exact correct option text",
  "explanation": "Educational explanation of why this answer is correct"
}}

VALIDATION CHECKLIST:
- Question is clear and specific
- Exactly 4 options provided (count them!)
- One correct answer, three plausible but incorrect distractors
- Correct answer matches exactly one of the options
- All options are roughly the same length
- No duplicate options

Return ONLY the JSON object, no additional text."""
        
        if not self.model:
            # Return fallback question if no API key
            return self._get_fallback_question(topic, difficulty)
        
        try:
            # Use sync version and run in thread if async fails
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Try to extract JSON if response has extra text
            if not response_text.startswith('{'):
                # Look for JSON block
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    response_text = response_text[start:end]
            
            # Parse the JSON response
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['question', 'options', 'correct_answer', 'explanation']
            if all(field in result for field in required_fields):
                # Validate exactly 4 options
                if isinstance(result['options'], list) and len(result['options']) == 4:
                    # Shuffle options to prevent always having correct answer in same position
                    result = self._shuffle_options(result)
                    return result
                else:
                    print(f"Invalid options count: got {len(result['options']) if isinstance(result['options'], list) else 'non-list'}, expected 4")
                    # Try to fix if we have too many options
                    if isinstance(result['options'], list) and len(result['options']) > 4:
                        result['options'] = result['options'][:4]
                        print(f"Truncated options to 4")
                        # Shuffle after truncation too
                        result = self._shuffle_options(result)
                        return result
                    else:
                        return self._get_fallback_question(topic, difficulty)
            else:
                print(f"Invalid response format: missing fields")
                return self._get_fallback_question(topic, difficulty)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text: {response.text[:200]}...")
            return self._get_fallback_question(topic, difficulty)
        except Exception as e:
            print(f"Error generating question: {e}")
            return self._get_fallback_question(topic, difficulty)
    
    async def generate_content(self, prompt: str) -> str:
        """Generate content using Gemini model"""
        gemini_logger = logger.getChild("gemini")
        gemini_logger.info(f"🤖 [GEMINI] generate_content called")
        gemini_logger.info(f"🤖 [GEMINI] Model initialized: {self.model is not None}")
        gemini_logger.info(f"🤖 [GEMINI] Prompt length: {len(prompt)} characters")
        gemini_logger.info(f"🤖 [GEMINI] Prompt preview: {prompt[:200]}...")
        
        if not self.model:
            gemini_logger.error(f"❌ [GEMINI] Model not initialized - raising exception")
            raise Exception("Gemini model not initialized")
        
        try:
            import asyncio
            import time
            
            # Add timing and run sync method in thread pool
            start_time = time.time()
            gemini_logger.info(f"🚀 [GEMINI] Starting Gemini API call at {start_time}")
            
            # Run the synchronous call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            gemini_logger.info(f"🔄 [GEMINI] Executing model.generate_content in thread pool...")
            response = await loop.run_in_executor(
                None, 
                self.model.generate_content, 
                prompt
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            gemini_logger.info(f"✅ [GEMINI] Gemini API completed in {elapsed_ms:.1f}ms")
            gemini_logger.info(f"📝 [GEMINI] Response length: {len(response.text) if response.text else 0} characters")
            gemini_logger.info(f"📝 [GEMINI] Response preview: {response.text[:200] if response.text else 'No text'}...")
            
            # Log to performance logger if slow
            if elapsed_ms > 3000:
                perf_logger = logger.getChild("performance")
                perf_logger.warning(f"SLOW GEMINI: API call took {elapsed_ms:.1f}ms")
            
            # If extremely slow (>30s), log as critical issue
            if elapsed_ms > 30000:
                error_logger = logger.getChild("errors")
                error_logger.error(f"CRITICAL: Gemini API took {elapsed_ms:.1f}ms - consider disabling AI generation temporarily")
            
            return response.text.strip()
        except Exception as e:
            error_logger = logger.getChild("errors")
            error_logger.error(f"❌ [GEMINI] Gemini API error: {e}")
            error_logger.error(f"📚 [GEMINI] Error stack trace:", exc_info=True)
            raise
    
    def _shuffle_options(self, question_data: Dict) -> Dict:
        """Shuffle the options randomly and update the correct_answer accordingly"""
        import random
        
        # DEBUG MODE: Skip shuffling and provide correct answer index for frontend highlighting
        debug_mode = True  # Enabled for fast debugging
        
        if debug_mode:
            # Don't shuffle in debug mode - keep original order
            options = question_data['options'].copy()
            correct_answer = question_data['correct_answer']
            
            # Find correct option index for frontend highlighting
            debug_correct_index = None
            for i, option in enumerate(options):
                if option == correct_answer or option.strip().lower() == correct_answer.strip().lower():
                    debug_correct_index = i
                    break
            
            question_data['options'] = options
            if debug_correct_index is not None:
                question_data['debug_correct_index'] = debug_correct_index
            return question_data
        
        # NORMAL MODE: Shuffle options
        # Get the original options and correct answer
        original_options = question_data['options'].copy()
        correct_answer = question_data['correct_answer']
        
        # Find the index of the correct answer
        try:
            correct_index = original_options.index(correct_answer)
        except ValueError:
            # If exact match fails, try case-insensitive search
            correct_index = None
            for i, option in enumerate(original_options):
                if option.strip().lower() == correct_answer.strip().lower():
                    correct_index = i
                    break
            
            # If still not found, return original (don't shuffle to avoid breaking)
            if correct_index is None:
                print(f"Warning: Correct answer '{correct_answer}' not found in options, skipping shuffle")
                return question_data
        
        # Create a list of indices and shuffle them
        indices = list(range(len(original_options)))
        random.shuffle(indices)
        
        # Reorder options according to shuffled indices
        shuffled_options = [original_options[i] for i in indices]
        
        # Find where the correct answer ended up after shuffling
        new_correct_index = indices.index(correct_index)
        new_correct_answer = shuffled_options[new_correct_index]
        
        # Update the question data
        question_data['options'] = shuffled_options
        question_data['correct_answer'] = new_correct_answer
        
        return question_data
    
    def _get_fallback_question(self, topic: str, difficulty: int) -> Dict:
        """Generate a fallback question when API is unavailable"""
        fallback_questions = {
            "easy": {
                "question": f"What is {topic}?",
                "options": [
                    f"{topic} is a type of algorithm",
                    f"{topic} is a programming language", 
                    f"{topic} is a data structure",
                    f"{topic} is a hardware component"
                ],
                "correct_answer": f"{topic} is a type of algorithm",
                "explanation": "This is a basic definition question to test fundamental understanding."
            },
            "medium": {
                "question": f"Which of the following is a key characteristic of {topic}?",
                "options": [
                    "It requires labeled data",
                    "It works without any data",
                    "It only works with images",
                    "It cannot be automated"
                ],
                "correct_answer": "It requires labeled data",
                "explanation": "Understanding the characteristics helps in practical application."
            },
            "hard": {
                "question": f"What is the computational complexity of typical {topic} algorithms?",
                "options": [
                    "O(n log n)",
                    "O(1)",
                    "O(2^n)",
                    "O(n^2)"
                ],
                "correct_answer": "O(n log n)",
                "explanation": "Advanced understanding includes computational complexity analysis."
            }
        }
        
        if difficulty <= 3:
            result = fallback_questions["easy"]
        elif difficulty <= 7:
            result = fallback_questions["medium"]
        else:
            result = fallback_questions["hard"]
        
        # Shuffle fallback questions too
        return self._shuffle_options(result)
    
    async def generate_quiz_questions(
        self,
        topic: str,
        num_questions: int = 5,
        difficulty_range: tuple = (1, 5)
    ) -> List[Dict]:
        """Generate multiple questions for a quiz"""
        questions = []
        
        for i in range(num_questions):
            # Vary difficulty within range
            difficulty = difficulty_range[0] + (i * (difficulty_range[1] - difficulty_range[0]) // num_questions)
            question = await self.generate_question(topic, difficulty)
            questions.append(question)
        
        return questions
    
    async def interpret_learning_request(
        self, 
        request_text: str, 
        existing_topics: List[Dict]
    ) -> Dict:
        """
        Interpret user's free text learning request and find optimal placement in ontology tree
        """
        
        # Prepare existing topics context, prioritizing exact/similar matches
        request_lower = request_text.lower()
        request_words = request_lower.split()
        
        # Sort topics to put potential matches first
        def match_score(topic):
            name_lower = topic['name'].lower()
            # Exact match gets highest score
            if name_lower == request_lower:
                return 100
            # Check for key words from request
            score = 0
            for word in request_words:
                if len(word) > 2 and word in name_lower:
                    score += 10
            return score
        
        sorted_topics = sorted(existing_topics, key=match_score, reverse=True)
        
        topics_context = "\n".join([
            f"- {topic['name']}: {topic.get('description', 'No description')} (Level: {topic.get('level', 0)})"
            for topic in sorted_topics[:25]  # Show more topics, prioritizing matches
        ])
        
        prompt = f"""You are an AI ontology manager. Your job is to determine if a user's learning request matches an existing topic or needs a new topic created.

User's request: "{request_text}"

Existing topics in our ontology (sorted by relevance):
{topics_context}

STEP-BY-STEP ANALYSIS PROCESS:

STEP 1: CHECK FOR EXACT MATCHES
- Look for topics that match the user's request exactly or very closely
- Consider variations like "Large Language Models" vs "Large Language Models (LLMs)"
- If you find an exact/near-exact match, SET already_exists=true and existing_topic_match to that topic name
- When exact match exists, use the EXISTING topic name as parsed_topic (don't create variations)

STEP 2: IF NO EXACT MATCH EXISTS
- Only then consider semantic similarity and parent placement
- Large Language Models/transformers/BERT/GPT → "Natural Language Processing" or "Modern AI"
- Image processing/CNN techniques → appropriate vision-related topics
- Reinforcement Learning → "Reinforcement Learning"

RESPOND WITH ONLY THIS JSON FORMAT:
{{
  "parsed_topic": "Use EXACT existing name if match found, otherwise create new name",
  "description": "What this topic covers",
  "main_concepts": ["concept1", "concept2", "concept3"],
  "suggested_parent": "Parent topic name or null",
  "confidence": 0.95,
  "difficulty_level": 4,
  "reasoning": "Your reasoning",
  "already_exists": false,
  "existing_topic_match": null,
  "semantic_matches": ["similar topics"]
}}

CRITICAL RULES:
1. If user asks for "Large Language Models" and you see "Large Language Models (LLMs)" in the list → already_exists=true, existing_topic_match="Large Language Models (LLMs)", parsed_topic="Large Language Models (LLMs)"
2. Don't create "Advanced" or other variations when exact matches exist
3. Exact match detection is THE TOP PRIORITY
4. Only do semantic analysis if no exact match exists

Respond with ONLY the JSON object, no additional text."""

        if not self.model:
            # Return fallback interpretation
            return self._get_fallback_interpretation(request_text)
        
        try:
            response_text = await self.generate_content(prompt)
            
            # Try to extract JSON if response has extra text
            if not response_text.startswith('{'):
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    response_text = response_text[start:end]
            
            # Parse the JSON response
            result = json.loads(response_text)
            
            # Validate required fields
            required_fields = ['parsed_topic', 'description', 'suggested_parent', 'confidence', 'difficulty_level']
            if all(field in result for field in required_fields):
                return result
            else:
                logger.warning(f"Invalid interpretation response format: missing fields")
                return self._get_fallback_interpretation(request_text)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in learning request interpretation: {e}")
            return self._get_fallback_interpretation(request_text)
        except Exception as e:
            logger.error(f"Error interpreting learning request: {e}")
            return self._get_fallback_interpretation(request_text)
    
    def _get_fallback_interpretation(self, request_text: str) -> Dict:
        """Generate a fallback interpretation when AI is unavailable"""
        
        # Simple keyword-based fallback
        request_lower = request_text.lower()
        
        # Common AI/ML keywords mapping
        keyword_mappings = {
            'computer vision': {
                'parent': 'Artificial Intelligence',
                'difficulty': 5,
                'description': 'Computer vision and image processing techniques'
            },
            'neural network': {
                'parent': 'Artificial Intelligence', 
                'difficulty': 6,
                'description': 'Neural networks and deep learning architectures'
            },
            'machine learning': {
                'parent': 'Artificial Intelligence',
                'difficulty': 4,
                'description': 'Machine learning algorithms and techniques'
            },
            'reinforcement learning': {
                'parent': 'Artificial Intelligence',
                'difficulty': 7,
                'description': 'Reinforcement learning and agent-based systems'
            }
        }
        
        # Find best match
        best_match = None
        for keyword, info in keyword_mappings.items():
            if keyword in request_lower:
                best_match = info
                break
        
        if not best_match:
            best_match = {
                'parent': 'Artificial Intelligence',
                'difficulty': 3,
                'description': 'AI-related topic based on user request'
            }
        
        # Extract topic name from request (simple approach)
        topic_name = request_text.strip().title()
        if len(topic_name) > 50:
            topic_name = topic_name[:47] + "..."
        
        return {
            "parsed_topic": topic_name,
            "description": best_match['description'],
            "main_concepts": [topic_name.lower()],
            "suggested_parent": best_match['parent'],
            "confidence": 0.6,
            "difficulty_level": best_match['difficulty'],
            "reasoning": "Fallback interpretation based on keyword matching",
            "already_exists": False,
            "existing_topic_match": None,
            "semantic_matches": []
        }

gemini_service = GeminiService()