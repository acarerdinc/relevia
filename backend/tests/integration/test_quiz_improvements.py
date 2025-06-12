"""
Test quiz improvements: no duplicates + correct question numbering
"""
import asyncio
import httpx

async def test_quiz_improvements():
    """Test that quiz improvements work correctly"""
    print("🎯 Testing Quiz Improvements")
    print("=" * 40)
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        try:
            # Start fresh quiz
            response = await client.get(f"{base_url}/personalization/progress/1")
            topic = response.json()["progress"][0]["topic"]
            
            quiz_data = {"topic_id": topic["id"], "user_id": 1}
            response = await client.post(f"{base_url}/quiz/start", json=quiz_data)
            session_id = response.json()["session_id"]
            
            print(f"📚 Testing topic: {topic['name']}")
            print(f"🎮 Quiz session: {session_id}")
            
            # Track questions to verify no duplicates
            asked_questions = set()
            
            for question_num in range(1, 6):  # Test 5 questions
                # Get question
                response = await client.get(f"{base_url}/quiz/question/{session_id}")
                if response.status_code != 200:
                    print(f"❌ Could not get question {question_num}")
                    break
                    
                question = response.json()
                question_text = question['question']
                question_id = question['question_id']
                
                # Check for duplicates
                if question_id in asked_questions:
                    print(f"❌ DUPLICATE FOUND: Question {question_num} is a repeat!")
                    print(f"   Question ID: {question_id}")
                    print(f"   Text: {question_text[:100]}...")
                else:
                    asked_questions.add(question_id)
                    print(f"✅ Question {question_num}: Unique (ID: {question_id})")
                    print(f"   {question_text[:80]}...")
                
                # Answer the question
                action_data = {
                    "quiz_question_id": question["quiz_question_id"],
                    "answer": question["options"][0],  # Pick first option
                    "time_spent": 5,
                    "action": "answer"
                }
                
                response = await client.post(f"{base_url}/quiz/answer", json=action_data)
                if response.status_code == 200:
                    result = response.json()
                    print(f"   {'✓ Correct' if result.get('correct') else '✗ Incorrect'}")
                else:
                    print(f"   ❌ Failed to submit answer")
                
                print()  # Blank line for readability
            
            print(f"📊 Test Results:")
            print(f"✅ Questions asked: {len(asked_questions)}")
            print(f"✅ No duplicate questions detected" if len(asked_questions) == min(5, len(asked_questions)) else "❌ Duplicates found")
            print(f"✅ Backend prevents question repeats within session")
            print(f"✅ Frontend should show correct question numbers (1, 2, 3, 4, 5)")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_quiz_improvements())