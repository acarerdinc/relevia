"""
Test major AI domains generation by forcing high proficiency
"""
import asyncio
import httpx
import json

async def test_forced_proficiency():
    """Test by ensuring high accuracy to trigger major domains unlock"""
    print("🎯 Testing Forced Proficiency for Major Domains")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        try:
            # Get AI topic
            response = await client.get(f"{base_url}/personalization/progress/1")
            ai_topic = response.json()["progress"][0]["topic"]
            
            # Start quiz
            quiz_data = {"topic_id": ai_topic["id"], "user_id": 1}
            response = await client.post(f"{base_url}/quiz/start", json=quiz_data)
            session_id = response.json()["session_id"]
            
            print(f"🎮 Quiz session: {session_id}")
            print(f"🎯 Target: Get 5+ questions with 80%+ accuracy to unlock major domains")
            
            # Answer questions with high accuracy
            correct_count = 0
            total_count = 0
            
            for i in range(6):  # Answer 6 questions
                # Get question
                response = await client.get(f"{base_url}/quiz/question/{session_id}")
                if response.status_code != 200:
                    print(f"❌ Failed to get question {i+1}")
                    break
                    
                question = response.json()
                
                # Get the correct answer from backend for testing (cheat to force high accuracy)
                # We'll choose the first option and see if it's correct, if not try others
                correct_answer_found = False
                
                for option_idx, option in enumerate(question["options"]):
                    action_data = {
                        "quiz_question_id": question["quiz_question_id"],
                        "answer": option,
                        "time_spent": 10,
                        "action": "answer"
                    }
                    
                    response = await client.post(f"{base_url}/quiz/answer", json=action_data)
                    if response.status_code == 200:
                        result = response.json()
                        total_count += 1
                        
                        if result.get("correct"):
                            correct_count += 1
                            correct_answer_found = True
                            print(f"✅ Question {i+1}: Correct ({option[:30]}...)")
                        else:
                            print(f"✗ Question {i+1}: Incorrect ({option[:30]}...)")
                        
                        # Check for unlocked topics
                        if result.get("unlocked_topics"):
                            unlocked_names = [t["name"] for t in result["unlocked_topics"]]
                            print(f"🎉 UNLOCKED: {unlocked_names}")
                            
                            # List the major domains that were unlocked
                            print(f"\n🌟 Major AI Domains Generated:")
                            for topic_info in result["unlocked_topics"]:
                                print(f"   ✨ {topic_info['name']}")
                                print(f"      {topic_info['description']}")
                            return  # Success! We got the unlock
                        
                        break  # Move to next question
                
                if not correct_answer_found and total_count > 0:
                    # Force the accuracy by manipulating our stats
                    print(f"   Trying to boost accuracy...")
            
            accuracy = correct_count / total_count if total_count > 0 else 0
            print(f"\n📊 Final Stats: {correct_count}/{total_count} ({accuracy:.1%})")
            
            if accuracy < 0.6:
                print(f"⚠️  Accuracy too low ({accuracy:.1%}) - need 60%+ to unlock")
                print(f"🔧 Let me try a different approach...")
                
                # Try using 'teach_me' actions to boost interest
                for i in range(3):
                    response = await client.get(f"{base_url}/quiz/question/{session_id}")
                    if response.status_code == 200:
                        question = response.json()
                        
                        action_data = {
                            "quiz_question_id": question["quiz_question_id"],
                            "answer": "",
                            "time_spent": 15,
                            "action": "teach_me"
                        }
                        
                        response = await client.post(f"{base_url}/quiz/answer", json=action_data)
                        if response.status_code == 200:
                            result = response.json()
                            print(f"🎓 Teach Me action {i+1} - building interest")
                            
                            if result.get("unlocked_topics"):
                                print(f"🎉 Topics unlocked via interest!")
                                for topic_info in result["unlocked_topics"]:
                                    print(f"   ✨ {topic_info['name']}")
                                return
            
            # Check final state
            response = await client.get(f"{base_url}/personalization/progress/1")
            final_progress = response.json()["progress"]
            unlocked_count = sum(1 for p in final_progress if p["is_unlocked"])
            
            print(f"\n📋 Final State: {unlocked_count} topics unlocked")
            for progress in final_progress:
                if progress["is_unlocked"]:
                    topic = progress["topic"]
                    print(f"   🔓 {topic['name']}")
                    
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_forced_proficiency())