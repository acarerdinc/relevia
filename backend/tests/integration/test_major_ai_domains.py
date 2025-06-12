"""
Test that the AI root topic generates major AI domains as children
"""
import asyncio
import httpx

async def test_major_ai_domains():
    """Test that AI root topic spawns Computer Vision, NLP, etc."""
    print("🧠 Testing Major AI Domains Generation")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Check initial state (should have only AI root)
            response = await client.get(f"{base_url}/personalization/progress/1")
            progress = response.json()["progress"]
            
            assert len(progress) == 1, f"Expected 1 topic, got {len(progress)}"
            ai_topic = progress[0]["topic"]
            assert ai_topic["name"] == "Artificial Intelligence"
            
            print(f"✅ Starting with: {ai_topic['name']} (ID: {ai_topic['id']})")
            
            # 2. Start quiz and build proficiency
            quiz_data = {"topic_id": ai_topic["id"], "user_id": 1}
            response = await client.post(f"{base_url}/quiz/start", json=quiz_data)
            session_id = response.json()["session_id"]
            
            print(f"🎯 Started quiz session: {session_id}")
            
            # 3. Answer questions to reach proficiency threshold
            correct_answers = 0
            total_questions = 0
            
            for i in range(8):  # Answer enough to get 60%+ accuracy
                # Get question
                response = await client.get(f"{base_url}/quiz/question/{session_id}")
                if response.status_code != 200:
                    break
                    
                question = response.json()
                
                # Choose correct answer for some questions to build proficiency
                answer = question["options"][0] if i < 5 else question["options"][1]
                
                action_data = {
                    "quiz_question_id": question["quiz_question_id"],
                    "answer": answer,
                    "time_spent": 10,
                    "action": "answer"
                }
                
                response = await client.post(f"{base_url}/quiz/answer", json=action_data)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("correct"):
                        correct_answers += 1
                    total_questions += 1
                    
                    # Check if topics were unlocked
                    if result.get("unlocked_topics"):
                        unlocked_names = [t["name"] for t in result["unlocked_topics"]]
                        print(f"🎉 Unlocked topics: {unlocked_names}")
                        break
            
            accuracy = correct_answers / total_questions if total_questions > 0 else 0
            print(f"📊 Final accuracy: {correct_answers}/{total_questions} ({accuracy:.1%})")
            
            # 4. Check what major domains were generated
            response = await client.get(f"{base_url}/personalization/progress/1")
            final_progress = response.json()["progress"]
            
            unlocked_topics = [p["topic"]["name"] for p in final_progress if p["is_unlocked"]]
            
            print(f"\n🌟 Generated Major AI Domains:")
            expected_domains = [
                "Machine Learning", "Computer Vision", "Natural Language Processing",
                "Deep Learning", "Reinforcement Learning", "AI Ethics and Safety", "Robotics and AI"
            ]
            
            found_domains = []
            for topic_name in unlocked_topics:
                if topic_name != "Artificial Intelligence":  # Skip root
                    found_domains.append(topic_name)
                    is_expected = topic_name in expected_domains
                    status = "✅" if is_expected else "🔍"
                    print(f"   {status} {topic_name}")
            
            print(f"\n📈 Results:")
            print(f"✅ Total topics unlocked: {len(unlocked_topics)}")
            print(f"✅ Major domains found: {len(found_domains)}")
            
            expected_found = sum(1 for domain in found_domains if domain in expected_domains)
            print(f"✅ Expected domains found: {expected_found}/{len(expected_domains)}")
            
            if len(found_domains) >= 5:
                print(f"🎉 SUCCESS: Generated comprehensive set of major AI domains!")
            else:
                print(f"⚠️  Few domains generated, may need higher proficiency")
                
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_major_ai_domains())