import google.generativeai as genai
from typing import Dict, List, Optional
from core.config import settings
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
                        print("⚠️  WARNING: Could not initialize any Gemini model.")
        else:
            self.model = None
            print("⚠️  WARNING: Gemini API key not configured. Question generation will use fallback questions.")
    
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

Respond with ONLY a valid JSON object in this exact format:
{{
  "question": "Clear, specific question about {topic}",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": "The exact correct option text",
  "explanation": "Educational explanation of why this answer is correct"
}}

Important: Return ONLY the JSON object, no additional text."""
        
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
                return result
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
        if not self.model:
            raise Exception("Gemini model not initialized")
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating content: {e}")
            raise
    
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
            return fallback_questions["easy"]
        elif difficulty <= 7:
            return fallback_questions["medium"]
        else:
            return fallback_questions["hard"]
    
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

gemini_service = GeminiService()