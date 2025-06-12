#!/usr/bin/env python3
"""
Test the adaptive learning API endpoints directly
"""
import asyncio
import httpx
import json
import sys
import time
from contextlib import asynccontextmanager

# Start the FastAPI server for testing
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the app
sys.path.append('.')
from main import app

async def test_api_endpoints():
    """Test the adaptive learning API endpoints"""
    
    print("🚀 Testing Adaptive Learning API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n=== Test 1: Health Check ===")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✓ Health check status: {response.status_code}")
            if response.status_code == 200:
                print(f"✓ Health response: {response.json()}")
        except Exception as e:
            print(f"✗ Health check failed: {e}")
        
        # Test 2: Start adaptive learning session
        print("\n=== Test 2: Start Adaptive Session ===")
        try:
            response = await client.post(f"{base_url}/api/v1/adaptive/start?user_id=1")
            print(f"✓ Start session status: {response.status_code}")
            if response.status_code == 200:
                session_data = response.json()
                print(f"✓ Session created: {session_data['session_id']}")
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
            response = await client.get(f"{base_url}/api/v1/adaptive/question/{session_id}")
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
            response = await client.post(f"{base_url}/api/v1/adaptive/answer", json=answer_data)
            print(f"✓ Submit answer status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Answer result: {result['correct']}")
                print(f"✓ Session progress: {result['session_progress']['total_questions']} questions")
                print(f"✓ Engagement level: {result['learning_insights']['engagement_level']}")
            else:
                print(f"✗ Submit answer failed: {response.text}")
        except Exception as e:
            print(f"✗ Submit answer failed: {e}")
        
        # Test 5: Continue learning (combined endpoint)
        print("\n=== Test 5: Continue Learning ===")
        try:
            response = await client.get(f"{base_url}/api/v1/adaptive/continue/1")
            print(f"✓ Continue learning status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Ready to learn: {result.get('ready_to_learn', False)}")
                if result.get('question'):
                    print(f"✓ Got question: {result['question']['topic_name']}")
                else:
                    print(f"✓ Message: {result.get('message', 'No message')}")
            else:
                print(f"✗ Continue learning failed: {response.text}")
        except Exception as e:
            print(f"✗ Continue learning failed: {e}")
        
        # Test 6: Learning dashboard
        print("\n=== Test 6: Learning Dashboard ===")
        try:
            response = await client.get(f"{base_url}/api/v1/adaptive/dashboard/1")
            print(f"✓ Dashboard status: {response.status_code}")
            if response.status_code == 200:
                dashboard = response.json()
                print(f"✓ Focus area: {dashboard['learning_state']['focus_area']}")
                print(f"✓ Readiness score: {dashboard['learning_state']['readiness_score']:.3f}")
                print(f"✓ Recommendations: {len(dashboard.get('recommendations', []))}")
            else:
                print(f"✗ Dashboard failed: {response.text}")
        except Exception as e:
            print(f"✗ Dashboard failed: {e}")
        
        # Test 7: Learning insights
        print("\n=== Test 7: Learning Insights ===")
        try:
            response = await client.get(f"{base_url}/api/v1/adaptive/insights/1")
            print(f"✓ Insights status: {response.status_code}")
            if response.status_code == 200:
                insights = response.json()
                print(f"✓ Learning style: {insights['summary']['learning_style']}")
                print(f"✓ Exploration coverage: {insights['summary']['exploration_coverage']:.3f}")
            else:
                print(f"✗ Insights failed: {response.text}")
        except Exception as e:
            print(f"✗ Insights failed: {e}")
        
        # Test 8: Multiple questions in sequence
        print("\n=== Test 8: Sequential Questions ===")
        for i in range(3):
            print(f"\n--- Question {i+1} ---")
            try:
                # Get question
                response = await client.get(f"{base_url}/api/v1/adaptive/question/{session_id}")
                if response.status_code == 200:
                    question_data = response.json()
                    print(f"✓ Question {i+1}: {question_data['topic_name']}")
                    
                    # Submit answer
                    answer_data = {
                        "quiz_question_id": question_data['quiz_question_id'],
                        "answer": "Option A" if i % 2 == 0 else "Option B",
                        "time_spent": 20 + i * 5,
                        "action": "answer"
                    }
                    answer_response = await client.post(f"{base_url}/api/v1/adaptive/answer", json=answer_data)
                    if answer_response.status_code == 200:
                        result = answer_response.json()
                        print(f"✓ Answer {i+1}: {result['correct']} (Progress: {result['session_progress']['total_questions']})")
                        
                        # Check for discoveries
                        if result.get('unlocked_topics'):
                            print(f"🎉 Unlocked {len(result['unlocked_topics'])} new topics!")
                    else:
                        print(f"✗ Answer {i+1} failed: {answer_response.status_code}")
                        break
                else:
                    print(f"✗ Question {i+1} failed: {response.status_code}")
                    if response.status_code == 404:
                        error_data = response.json()
                        print(f"  Error: {error_data.get('detail', 'Unknown error')}")
                    break
            except Exception as e:
                print(f"✗ Sequential question {i+1} failed: {e}")
                break

async def run_server_and_test():
    """Run the server and execute tests"""
    
    # Modify the database URL to use our test database
    import os
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_adaptive.db'
    
    # Configure uvicorn
    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=8001,
        log_level="error",  # Suppress server logs during testing
        access_log=False
    )
    server = uvicorn.Server(config)
    
    # Start server in background
    import threading
    server_thread = threading.Thread(target=server.run)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    # Run tests
    await test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("🏁 API Testing Complete")

if __name__ == "__main__":
    asyncio.run(run_server_and_test())