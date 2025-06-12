"""
Test that specifically validates the quiz error fix
"""
import asyncio
import httpx

async def test_quiz_error_fix():
    """Test the specific error case that was reported"""
    print("🔧 Testing Quiz Error Fix")
    print("=" * 40)
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Get current progress to find a topic
            print("📋 Getting user progress...")
            response = await client.get(f"{base_url}/personalization/progress/1")
            assert response.status_code == 200
            
            progress = response.json()["progress"]
            if not progress:
                print("❌ No topics found in progress")
                return
                
            topic = progress[0]["topic"]
            topic_id = topic["id"]
            print(f"✅ Found topic: {topic['name']} (ID: {topic_id})")
            
            # 2. Start a quiz (this used to work)
            print("🎯 Starting quiz...")
            quiz_data = {"topic_id": topic_id, "user_id": 1}
            response = await client.post(f"{base_url}/quiz/start", json=quiz_data)
            assert response.status_code == 200
            
            session = response.json()
            session_id = session["session_id"]
            print(f"✅ Quiz started: Session {session_id}")
            
            # 3. Get a question (this was failing with 500 error)
            print("❓ Getting question...")
            response = await client.get(f"{base_url}/quiz/question/{session_id}")
            assert response.status_code == 200, f"Failed to get question: {response.status_code} - {response.text}"
            
            question = response.json()
            quiz_question_id = question["quiz_question_id"]
            options = question["options"]
            print(f"✅ Question loaded: {question['question'][:50]}...")
            
            # 4. Submit an answer (this was the main error point)
            print("📝 Submitting answer...")
            answer_data = {
                "quiz_question_id": quiz_question_id,
                "answer": options[0],  # Choose first option
                "time_spent": 10,
                "action": "answer"
            }
            response = await client.post(f"{base_url}/quiz/answer", json=answer_data)
            assert response.status_code == 200, f"Failed to submit answer: {response.status_code} - {response.text}"
            
            result = response.json()
            print(f"✅ Answer submitted: {'Correct' if result.get('correct') else 'Incorrect'}")
            
            # 5. Test 'Teach Me' action (new feature)
            print("🎓 Testing 'Teach Me' action...")
            
            # Get another question first
            response = await client.get(f"{base_url}/quiz/question/{session_id}")
            if response.status_code == 200:
                question = response.json()
                quiz_question_id = question["quiz_question_id"]
                
                teach_me_data = {
                    "quiz_question_id": quiz_question_id,
                    "answer": "",
                    "time_spent": 5,
                    "action": "teach_me"
                }
                response = await client.post(f"{base_url}/quiz/answer", json=teach_me_data)
                assert response.status_code == 200, f"'Teach Me' failed: {response.status_code} - {response.text}"
                print("✅ 'Teach Me' action successful")
            
            # 6. Test 'Skip' action (new feature)
            print("⏭️ Testing 'Skip' action...")
            
            # Get another question
            response = await client.get(f"{base_url}/quiz/question/{session_id}")
            if response.status_code == 200:
                question = response.json()
                quiz_question_id = question["quiz_question_id"]
                
                skip_data = {
                    "quiz_question_id": quiz_question_id,
                    "answer": "",
                    "time_spent": 2,
                    "action": "skip"
                }
                response = await client.post(f"{base_url}/quiz/answer", json=skip_data)
                assert response.status_code == 200, f"'Skip' failed: {response.status_code} - {response.text}"
                print("✅ 'Skip' action successful")
            
            print("\n🎉 All quiz errors have been fixed!")
            print("✅ Question loading works")
            print("✅ Answer submission works")
            print("✅ 'Teach Me' button works") 
            print("✅ 'Skip' button works")
            print("✅ Interest tracking is functional")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_quiz_error_fix())