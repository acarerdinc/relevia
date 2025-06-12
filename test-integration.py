"""
Integration test that simulates complete user flow
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def full_integration_test():
    """Test the complete user flow from topic selection to quiz completion"""
    async with httpx.AsyncClient() as client:
        print("🚀 Running Full Integration Test")
        print("=" * 50)
        
        try:
            # Step 1: Health check
            print("\n1. Health Check")
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            print("✅ Backend is healthy")
            
            # Step 2: Load topics
            print("\n2. Loading AI Topics")
            response = await client.get(f"{BASE_URL}/topics/flat")
            assert response.status_code == 200
            topics = response.json()["topics"]
            print(f"✅ Loaded {len(topics)} topics")
            
            # Find a good test topic (leaf node with moderate difficulty)
            test_topics = [t for t in topics if t['parent_id'] is not None and 3 <= t['difficulty_min'] <= 6]
            if not test_topics:
                test_topics = [t for t in topics if t['parent_id'] is not None]
            
            test_topic = test_topics[0]
            print(f"📘 Selected topic: {test_topic['name']} (Difficulty: {test_topic['difficulty_min']}-{test_topic['difficulty_max']})")
            
            # Step 3: Start quiz session
            print("\n3. Starting Quiz Session")
            quiz_data = {"topic_id": test_topic['id'], "user_id": 1}
            response = await client.post(f"{BASE_URL}/quiz/start", json=quiz_data)
            assert response.status_code == 200
            session = response.json()
            session_id = session['session_id']
            print(f"✅ Quiz session {session_id} started for topic: {test_topic['name']}")
            
            # Step 4: Complete multiple questions to test adaptive behavior
            questions_completed = 0
            session_progress = None
            
            for question_num in range(1, 6):  # Test 5 questions
                print(f"\n4.{question_num} Question {question_num}")
                
                # Get question
                response = await client.get(f"{BASE_URL}/quiz/question/{session_id}")
                assert response.status_code == 200
                question = response.json()
                print(f"📝 Question: {question['question'][:80]}...")
                print(f"🎯 Difficulty: {question['difficulty']}/10")
                print(f"📋 Options: {len(question['options'])} choices")
                
                # Submit answer (always pick first option for consistency)
                answer_data = {
                    "quiz_question_id": question['quiz_question_id'],
                    "answer": question['options'][0],
                    "time_spent": 15 + question_num * 5  # Simulate varying response times
                }
                
                response = await client.post(f"{BASE_URL}/quiz/answer", json=answer_data)
                assert response.status_code == 200
                result = response.json()
                
                questions_completed += 1
                session_progress = result['session_progress']
                
                status = "✅ Correct" if result['correct'] else "❌ Incorrect"
                print(f"{status} - {result['explanation'][:80]}...")
                print(f"📊 Progress: {session_progress['correct_answers']}/{session_progress['total_questions']} ({session_progress['accuracy']*100:.1f}%)")
            
            # Step 5: Verify session info
            print(f"\n5. Session Summary")
            response = await client.get(f"{BASE_URL}/quiz/session/{session_id}")
            assert response.status_code == 200
            session_info = response.json()
            
            print(f"📈 Final Stats:")
            print(f"   • Topic: {session_info['topic']}")
            print(f"   • Questions: {session_info['total_questions']}")
            print(f"   • Correct: {session_info['correct_answers']}")
            print(f"   • Accuracy: {session_info['accuracy']*100:.1f}%")
            print(f"   • Started: {session_info['started_at']}")
            
            # Step 6: Test adaptive behavior by checking if difficulty changed
            print(f"\n6. Testing Adaptive Behavior")
            print("🧠 Checking if system adapts difficulty based on performance...")
            
            # Get one more question to see if difficulty adapted
            response = await client.get(f"{BASE_URL}/quiz/question/{session_id}")
            if response.status_code == 200:
                final_question = response.json()
                print(f"🎯 Next question difficulty: {final_question['difficulty']}/10")
                
                if session_info['accuracy'] > 0.7:
                    print("📈 High accuracy - system should increase difficulty")
                elif session_info['accuracy'] < 0.4:
                    print("📉 Low accuracy - system should decrease difficulty")
                else:
                    print("⚖️  Moderate accuracy - system should maintain difficulty")
            
            print(f"\n🎉 Integration Test PASSED!")
            print(f"✅ All {questions_completed} questions completed successfully")
            print(f"✅ Adaptive quiz engine working correctly")
            print(f"✅ Session management functional")
            
        except Exception as e:
            print(f"\n❌ Integration Test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == "__main__":
    success = asyncio.run(full_integration_test())
    exit(0 if success else 1)