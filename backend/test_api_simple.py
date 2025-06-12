#!/usr/bin/env python3
"""
Simple test of API endpoints using test client
"""
import asyncio
import sys
import os
from fastapi.testclient import TestClient

# Set test database
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_adaptive.db'

sys.path.append('.')
from main import app

def test_adaptive_api():
    """Test adaptive learning API with test client"""
    
    print("🚀 Testing Adaptive Learning API")
    print("=" * 40)
    
    client = TestClient(app)
    
    # Test 1: Health check
    print("\n=== Test 1: Health Check ===")
    try:
        response = client.get("/health")
        print(f"✓ Health status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Health response: {response.json()}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
    
    # Test 2: Start adaptive session
    print("\n=== Test 2: Start Adaptive Session ===")
    try:
        response = client.post("/api/v1/adaptive/start?user_id=1")
        print(f"✓ Start session status: {response.status_code}")
        if response.status_code == 200:
            session_data = response.json()
            print(f"✓ Session ID: {session_data['session_id']}")
            print(f"✓ Session type: {session_data['session_type']}")
            session_id = session_data['session_id']
        else:
            print(f"✗ Start session failed: {response.text}")
            return
    except Exception as e:
        print(f"✗ Start session failed: {e}")
        return
    
    # Test 3: Get next question
    print("\n=== Test 3: Get Next Question ===")
    try:
        response = client.get(f"/api/v1/adaptive/question/{session_id}")
        print(f"✓ Get question status: {response.status_code}")
        if response.status_code == 200:
            question_data = response.json()
            print(f"✓ Question ID: {question_data['question_id']}")
            print(f"✓ Topic: {question_data['topic_name']}")
            print(f"✓ Difficulty: {question_data['difficulty']}")
            print(f"✓ Options: {len(question_data['options'])} choices")
            quiz_question_id = question_data['quiz_question_id']
        else:
            print(f"✗ Get question failed: {response.text}")
            return
    except Exception as e:
        print(f"✗ Get question failed: {e}")
        return
    
    # Test 4: Submit answer
    print("\n=== Test 4: Submit Answer ===")
    try:
        answer_data = {
            "quiz_question_id": quiz_question_id,
            "answer": "Option A",
            "time_spent": 15,
            "action": "answer"
        }
        response = client.post("/api/v1/adaptive/answer", json=answer_data)
        print(f"✓ Submit answer status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Answer correct: {result['correct']}")
            print(f"✓ Progress: {result['session_progress']['total_questions']} questions")
            print(f"✓ Engagement: {result['learning_insights']['engagement_level']}")
        else:
            print(f"✗ Submit answer failed: {response.text}")
    except Exception as e:
        print(f"✗ Submit answer failed: {e}")
    
    # Test 5: Continue learning
    print("\n=== Test 5: Continue Learning ===")
    try:
        response = client.get("/api/v1/adaptive/continue/1")
        print(f"✓ Continue status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Ready to learn: {result.get('ready_to_learn', False)}")
            if result.get('question'):
                print(f"✓ Question topic: {result['question']['topic_name']}")
        else:
            print(f"✗ Continue failed: {response.text}")
    except Exception as e:
        print(f"✗ Continue failed: {e}")
    
    # Test 6: Sequential questions (test the issue after 2-3 questions)
    print("\n=== Test 6: Sequential Questions (Testing 2-3 Question Issue) ===")
    
    # Start a fresh session
    response = client.post("/api/v1/adaptive/start?user_id=1")
    if response.status_code != 200:
        print("✗ Could not start fresh session for sequential test")
        return
    
    fresh_session_id = response.json()['session_id']
    print(f"✓ Fresh session: {fresh_session_id}")
    
    for i in range(5):  # Try 5 questions to see where it breaks
        print(f"\n--- Sequential Question {i+1} ---")
        
        # Get question
        response = client.get(f"/api/v1/adaptive/question/{fresh_session_id}")
        if response.status_code == 200:
            question_data = response.json()
            print(f"✓ Q{i+1}: {question_data['topic_name']} (Difficulty: {question_data['difficulty']})")
            
            # Submit answer
            answer_data = {
                "quiz_question_id": question_data['quiz_question_id'],
                "answer": "Option A" if i % 2 == 0 else "Option B",
                "time_spent": 20,
                "action": "answer"
            }
            answer_response = client.post("/api/v1/adaptive/answer", json=answer_data)
            if answer_response.status_code == 200:
                result = answer_response.json()
                print(f"✓ A{i+1}: {result['correct']} (Total: {result['session_progress']['total_questions']})")
                
                # Check for unlocked topics
                if result.get('unlocked_topics'):
                    print(f"🎉 Unlocked {len(result['unlocked_topics'])} topics")
            else:
                print(f"✗ Answer {i+1} failed: {answer_response.status_code}")
                print(f"   Error: {answer_response.text}")
                break
        else:
            print(f"✗ Question {i+1} failed: {response.status_code}")
            if response.status_code == 404:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown')}")
            print(f"   Response: {response.text}")
            break
    
    # Test 7: Dashboard
    print("\n=== Test 7: Dashboard ===")
    try:
        response = client.get("/api/v1/adaptive/dashboard/1")
        print(f"✓ Dashboard status: {response.status_code}")
        if response.status_code == 200:
            dashboard = response.json()
            print(f"✓ Focus: {dashboard['learning_state']['focus_area']}")
            print(f"✓ Readiness: {dashboard['learning_state']['readiness_score']:.3f}")
        else:
            print(f"✗ Dashboard failed: {response.text}")
    except Exception as e:
        print(f"✗ Dashboard failed: {e}")
    
    print("\n" + "=" * 40)
    print("🏁 API Testing Complete")

if __name__ == "__main__":
    test_adaptive_api()