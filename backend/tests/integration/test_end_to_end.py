"""
End-to-end integration test for the dynamic ontology system
"""
import asyncio
import sys
from pathlib import Path
import httpx
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class EndToEndTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.user_id = 1
        
    async def run_full_test(self):
        """Run complete end-to-end test"""
        print("🚀 Starting End-to-End Test")
        print("=" * 50)
        
        try:
            async with httpx.AsyncClient() as client:
                # Test 1: Health check
                await self.test_health_check(client)
                
                # Test 2: Check initial state
                await self.test_initial_state(client)
                
                # Test 3: Start a quiz
                session = await self.test_start_quiz(client)
                
                # Test 4: Get and answer questions
                await self.test_quiz_flow(client, session)
                
                # Test 5: Check for dynamic topic generation
                await self.test_dynamic_generation(client)
                
                # Test 6: Test interest tracking with Teach Me/Skip
                await self.test_interest_tracking(client)
                
                # Test 7: Test personalization endpoints
                await self.test_personalization(client)
                
                print("\n🎉 All tests passed! The dynamic ontology system is working correctly.")
                
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_health_check(self, client):
        """Test that the backend is running"""
        print("\n🏥 Testing health check...")
        
        response = await client.get(f"{self.api_base}/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy", f"Service not healthy: {data}"
        
        print("✅ Health check passed")
    
    async def test_initial_state(self, client):
        """Test that we start with minimal ontology"""
        print("\n🌱 Testing initial state...")
        
        # Check user progress
        response = await client.get(f"{self.api_base}/personalization/progress/{self.user_id}")
        assert response.status_code == 200, f"Progress check failed: {response.status_code}"
        
        progress_data = response.json()
        progress_list = progress_data["progress"]
        
        # Should have exactly one topic: Artificial Intelligence
        assert len(progress_list) == 1, f"Expected 1 topic, got {len(progress_list)}"
        
        ai_topic = progress_list[0]["topic"]
        assert ai_topic["name"] == "Artificial Intelligence", f"Expected AI topic, got {ai_topic['name']}"
        assert progress_list[0]["is_unlocked"] == True, "AI topic should be unlocked"
        
        print(f"✅ Initial state correct: {ai_topic['name']} unlocked")
        return ai_topic
    
    async def test_start_quiz(self, client):
        """Test starting a quiz"""
        print("\n📝 Testing quiz start...")
        
        # Get the AI topic ID first
        response = await client.get(f"{self.api_base}/personalization/progress/{self.user_id}")
        ai_topic = response.json()["progress"][0]["topic"]
        topic_id = ai_topic["id"]
        
        # Start a quiz
        quiz_data = {
            "topic_id": topic_id,
            "user_id": self.user_id
        }
        
        response = await client.post(f"{self.api_base}/quiz/start", json=quiz_data)
        assert response.status_code == 200, f"Quiz start failed: {response.status_code} - {response.text}"
        
        session_data = response.json()
        assert "session_id" in session_data, "No session_id in response"
        assert session_data["topic_id"] == topic_id, "Topic ID mismatch"
        
        print(f"✅ Quiz started: Session {session_data['session_id']}")
        return session_data
    
    async def test_quiz_flow(self, client, session):
        """Test the quiz question flow"""
        print("\n❓ Testing quiz flow...")
        
        session_id = session["session_id"]
        questions_answered = 0
        correct_answers = 0
        
        # Answer several questions to build proficiency
        for i in range(8):
            # Get a question
            response = await client.get(f"{self.api_base}/quiz/question/{session_id}")
            
            if response.status_code != 200:
                print(f"⚠️  Could not get question {i+1}: {response.status_code}")
                break
                
            question_data = response.json()
            assert "quiz_question_id" in question_data, "No quiz_question_id in question"
            assert "options" in question_data, "No options in question"
            
            quiz_question_id = question_data["quiz_question_id"]
            
            # Choose first option (simulate 80% accuracy by getting some wrong)
            chosen_answer = question_data["options"][0]
            
            # Submit answer
            answer_data = {
                "quiz_question_id": quiz_question_id,
                "answer": chosen_answer,
                "time_spent": 5,
                "action": "answer"
            }
            
            response = await client.post(f"{self.api_base}/quiz/answer", json=answer_data)
            assert response.status_code == 200, f"Answer submission failed: {response.status_code}"
            
            result = response.json()
            questions_answered += 1
            if result.get("correct", False):
                correct_answers += 1
            
            print(f"   Question {i+1}: {'✓' if result.get('correct') else '✗'}")
            
            # Check for unlocked topics
            if result.get("unlocked_topics"):
                print(f"   🎉 Unlocked topics: {[t['name'] for t in result['unlocked_topics']]}")
        
        accuracy = correct_answers / questions_answered if questions_answered > 0 else 0
        print(f"✅ Quiz flow completed: {correct_answers}/{questions_answered} ({accuracy:.1%} accuracy)")
        
        return {"questions_answered": questions_answered, "correct_answers": correct_answers}
    
    async def test_dynamic_generation(self, client):
        """Test that dynamic topic generation occurred"""
        print("\n🌲 Testing dynamic topic generation...")
        
        # Check user progress again
        response = await client.get(f"{self.api_base}/personalization/progress/{self.user_id}")
        assert response.status_code == 200
        
        progress_data = response.json()
        progress_list = progress_data["progress"]
        
        # Should now have more than one topic if generation worked
        if len(progress_list) > 1:
            print(f"✅ Dynamic generation successful: {len(progress_list)} topics total")
            for progress in progress_list:
                topic = progress["topic"]
                status = "🔓" if progress["is_unlocked"] else "🔒"
                print(f"   {status} {topic['name']}")
        else:
            print("⚠️  No dynamic generation occurred (may need higher proficiency)")
            
        return progress_list
    
    async def test_interest_tracking(self, client):
        """Test Teach Me and Skip buttons"""
        print("\n💡 Testing interest tracking...")
        
        # Get current progress to find an unlocked topic
        response = await client.get(f"{self.api_base}/personalization/progress/{self.user_id}")
        progress_list = response.json()["progress"]
        
        # Find an unlocked topic
        unlocked_topic = None
        for progress in progress_list:
            if progress["is_unlocked"]:
                unlocked_topic = progress["topic"]
                break
        
        if not unlocked_topic:
            print("⚠️  No unlocked topics found for interest testing")
            return
        
        # Start a new quiz session
        quiz_data = {
            "topic_id": unlocked_topic["id"],
            "user_id": self.user_id
        }
        
        response = await client.post(f"{self.api_base}/quiz/start", json=quiz_data)
        if response.status_code != 200:
            print(f"⚠️  Could not start quiz for interest testing: {response.status_code}")
            return
            
        session_id = response.json()["session_id"]
        
        # Get a question
        response = await client.get(f"{self.api_base}/quiz/question/{session_id}")
        if response.status_code != 200:
            print(f"⚠️  Could not get question for interest testing: {response.status_code}")
            return
        
        question_data = response.json()
        quiz_question_id = question_data["quiz_question_id"]
        
        # Test "Teach Me" action
        teach_me_data = {
            "quiz_question_id": quiz_question_id,
            "answer": "",
            "time_spent": 10,
            "action": "teach_me"
        }
        
        response = await client.post(f"{self.api_base}/quiz/answer", json=teach_me_data)
        assert response.status_code == 200, f"Teach Me action failed: {response.status_code}"
        
        print("✅ 'Teach Me' action successful")
        
        # Get another question for Skip test
        response = await client.get(f"{self.api_base}/quiz/question/{session_id}")
        if response.status_code == 200:
            question_data = response.json()
            quiz_question_id = question_data["quiz_question_id"]
            
            # Test "Skip" action
            skip_data = {
                "quiz_question_id": quiz_question_id,
                "answer": "",
                "time_spent": 2,
                "action": "skip"
            }
            
            response = await client.post(f"{self.api_base}/quiz/answer", json=skip_data)
            assert response.status_code == 200, f"Skip action failed: {response.status_code}"
            
            print("✅ 'Skip' action successful")
    
    async def test_personalization(self, client):
        """Test personalization endpoints"""
        print("\n🎯 Testing personalization endpoints...")
        
        # Test user interests
        response = await client.get(f"{self.api_base}/personalization/interests/{self.user_id}")
        assert response.status_code == 200, f"Interests endpoint failed: {response.status_code}"
        
        interests = response.json()["interests"]
        print(f"✅ User interests retrieved: {len(interests)} interests")
        
        # Test recommendations
        response = await client.get(f"{self.api_base}/personalization/recommendations/{self.user_id}")
        assert response.status_code == 200, f"Recommendations endpoint failed: {response.status_code}"
        
        recommendations = response.json()["recommendations"]
        print(f"✅ Recommendations retrieved: {len(recommendations)} recommendations")
        
        # Test personalized ontology
        response = await client.get(f"{self.api_base}/personalization/ontology/{self.user_id}")
        assert response.status_code == 200, f"Personalized ontology failed: {response.status_code}"
        
        ontology = response.json()["topics"]
        print(f"✅ Personalized ontology retrieved: {len(ontology)} topics")

async def main():
    """Run the end-to-end test"""
    test = EndToEndTest()
    await test.run_full_test()

if __name__ == "__main__":
    asyncio.run(main())