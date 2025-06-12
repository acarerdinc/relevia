#!/usr/bin/env python3
"""
Comprehensive test script for the adaptive learning system
"""
import asyncio
import json
import sys
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, and_

# Import models and services
sys.path.append('.')
from db.models import Base, Topic, Question, User, UserSkillProgress, UserInterest, QuizSession, QuizQuestion
from services.adaptive_quiz_service import adaptive_quiz_service
from services.adaptive_question_selector import adaptive_question_selector
from services.adaptive_interest_tracker import adaptive_interest_tracker

# Setup test database
engine = create_async_engine('sqlite+aiosqlite:///./test_relevia.db', echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def setup_test_database():
    """Create tables and add test data"""
    print("=== Setting up test database ===")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as db:
        # Create test user
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True
        )
        db.add(user)
        
        # Create test topics
        topics = [
            Topic(id=1, name="Machine Learning Basics", description="Fundamentals of ML", difficulty_min=1, difficulty_max=5),
            Topic(id=2, name="Deep Learning", description="Neural networks and deep learning", difficulty_min=3, difficulty_max=8),
            Topic(id=3, name="Natural Language Processing", description="NLP fundamentals", difficulty_min=2, difficulty_max=7),
            Topic(id=4, name="Computer Vision", description="Image processing and CV", difficulty_min=4, difficulty_max=9),
            Topic(id=5, name="Reinforcement Learning", description="RL algorithms", difficulty_min=6, difficulty_max=10),
        ]
        
        for topic in topics:
            db.add(topic)
        
        await db.flush()
        
        # Create test questions for each topic
        questions = []
        for topic in topics:
            for i in range(5):  # 5 questions per topic
                question = Question(
                    topic_id=topic.id,
                    content=f"What is a key concept in {topic.name}? (Question {i+1})",
                    question_type="multiple_choice",
                    options=["Option A", "Option B", "Option C", "Option D"],
                    correct_answer="Option A",
                    explanation=f"This is the explanation for {topic.name} question {i+1}",
                    difficulty=min(topic.difficulty_max, max(topic.difficulty_min, i + 2))
                )
                questions.append(question)
                db.add(question)
        
        # Create initial user progress for unlocked topics
        for topic in topics[:3]:  # Unlock first 3 topics
            progress = UserSkillProgress(
                user_id=1,
                topic_id=topic.id,
                skill_level=0.3 + (topic.id * 0.1),  # Varying skill levels
                confidence=0.4 + (topic.id * 0.05),
                questions_answered=topic.id * 2,  # Some previous activity
                correct_answers=topic.id,
                mastery_level="novice" if topic.id == 1 else "beginner",
                is_unlocked=True,
                unlocked_at=datetime.utcnow()
            )
            db.add(progress)
        
        # Create some initial interest data
        for topic in topics[:3]:
            interest = UserInterest(
                user_id=1,
                topic_id=topic.id,
                interest_score=0.4 + (topic.id * 0.1),
                interaction_count=topic.id * 3,
                time_spent=topic.id * 300,  # 5 minutes per topic_id
                preference_type="implicit"
            )
            db.add(interest)
        
        await db.commit()
        print(f"✓ Created {len(topics)} topics, {len(questions)} questions, and progress data")

async def test_database_state():
    """Test 1: Check database state"""
    print("\n=== Test 1: Database State ===")
    
    async with AsyncSessionLocal() as db:
        # Count topics
        topic_count = await db.execute(select(func.count(Topic.id)))
        total_topics = topic_count.scalar()
        
        # Count questions
        question_count = await db.execute(select(func.count(Question.id)))
        total_questions = question_count.scalar()
        
        # Count questions with valid options
        valid_question_count = await db.execute(
            select(func.count(Question.id)).where(Question.options.isnot(None))
        )
        valid_questions = valid_question_count.scalar()
        
        # Check user progress
        progress_count = await db.execute(
            select(func.count(UserSkillProgress.id)).where(
                and_(UserSkillProgress.user_id == 1, UserSkillProgress.is_unlocked == True)
            )
        )
        unlocked_topics = progress_count.scalar()
        
        print(f"✓ Total topics: {total_topics}")
        print(f"✓ Total questions: {total_questions}")
        print(f"✓ Questions with valid options: {valid_questions}")
        print(f"✓ Unlocked topics for user: {unlocked_topics}")
        
        # Sample question data
        sample_question = await db.execute(
            select(Question).limit(1)
        )
        question = sample_question.scalar_one_or_none()
        if question:
            print(f"✓ Sample question options: {question.options}")
            print(f"✓ Sample question type: {question.question_type}")
        
        return {
            'total_topics': total_topics,
            'total_questions': total_questions,
            'valid_questions': valid_questions,
            'unlocked_topics': unlocked_topics
        }

async def test_adaptive_session_creation():
    """Test 2: Adaptive session creation"""
    print("\n=== Test 2: Adaptive Session Creation ===")
    
    async with AsyncSessionLocal() as db:
        try:
            # Start adaptive session
            session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id=1)
            print(f"✓ Session created: {session_data}")
            
            # Verify session in database
            session_result = await db.execute(
                select(QuizSession).where(QuizSession.id == session_data['session_id'])
            )
            session = session_result.scalar_one_or_none()
            
            if session:
                print(f"✓ Session verified in DB - Type: {session.session_type}")
                print(f"✓ Session user_id: {session.user_id}")
                print(f"✓ Session topic_id: {session.topic_id} (should be None for adaptive)")
                return session_data
            else:
                print("✗ Session not found in database")
                return None
                
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return None

async def test_question_selection():
    """Test 3: Question selection logic"""
    print("\n=== Test 3: Question Selection Logic ===")
    
    async with AsyncSessionLocal() as db:
        try:
            # Start session first
            session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id=1)
            session_id = session_data['session_id']
            
            # Test question selection multiple times
            questions_selected = []
            for i in range(5):
                print(f"\n--- Question Selection Attempt {i+1} ---")
                
                question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
                
                if question_data and "error" not in question_data:
                    questions_selected.append(question_data)
                    print(f"✓ Question selected: ID {question_data['question_id']}")
                    print(f"  Topic: {question_data['topic_name']}")
                    print(f"  Difficulty: {question_data['difficulty']}")
                    print(f"  Strategy: {question_data.get('selection_strategy', 'unknown')}")
                    print(f"  UCB Score: {question_data.get('topic_ucb_score', 0):.3f}")
                    print(f"  Options: {len(question_data.get('options', []))} choices")
                else:
                    print(f"✗ Question selection failed: {question_data}")
                    break
            
            print(f"\n✓ Successfully selected {len(questions_selected)} questions")
            
            # Check for diversity in topic selection
            topics_used = set(q['topic_id'] for q in questions_selected)
            print(f"✓ Topics covered: {len(topics_used)} different topics")
            
            return questions_selected
            
        except Exception as e:
            print(f"✗ Question selection failed: {e}")
            return []

async def test_answer_submission():
    """Test 4: Answer submission and processing"""
    print("\n=== Test 4: Answer Submission ===")
    
    async with AsyncSessionLocal() as db:
        try:
            # Start session and get a question
            session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id=1)
            session_id = session_data['session_id']
            
            question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
            
            if not question_data or "error" in question_data:
                print("✗ Could not get question for testing")
                return False
            
            quiz_question_id = question_data['quiz_question_id']
            correct_answer = "Option A"  # We know this from our test data
            
            print(f"Testing answer submission for question ID: {quiz_question_id}")
            
            # Test different types of answers
            test_cases = [
                {"answer": correct_answer, "action": "answer", "description": "Correct answer"},
                {"answer": "Option B", "action": "answer", "description": "Incorrect answer"},
                {"action": "teach_me", "description": "Teach me action"},
                {"action": "skip", "description": "Skip action"}
            ]
            
            for i, test_case in enumerate(test_cases):
                # Get a new question for each test
                if i > 0:
                    question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
                    if not question_data or "error" in question_data:
                        print(f"✗ Could not get question {i+1}")
                        continue
                    quiz_question_id = question_data['quiz_question_id']
                
                print(f"\n--- Testing: {test_case['description']} ---")
                
                response = await adaptive_quiz_service.submit_adaptive_answer(
                    db=db,
                    quiz_question_id=quiz_question_id,
                    user_answer=test_case.get("answer"),
                    time_spent=15,
                    action=test_case["action"]
                )
                
                print(f"✓ Response received: {test_case['description']}")
                print(f"  Action: {response.get('action')}")
                print(f"  Correct: {response.get('correct')}")
                print(f"  Session progress: {response.get('session_progress', {}).get('total_questions')} questions")
                
                if response.get('learning_insights'):
                    insights = response['learning_insights']
                    print(f"  Engagement: {insights.get('engagement_level', 0):.3f}")
                    print(f"  Learning progress: {insights.get('learning_progress', 0):.3f}")
            
            return True
            
        except Exception as e:
            print(f"✗ Answer submission failed: {e}")
            return False

async def test_bandit_algorithm():
    """Test 5: Multi-armed bandit algorithm behavior"""
    print("\n=== Test 5: Multi-Armed Bandit Algorithm ===")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get unlocked topics for user
            unlocked_topics = await adaptive_question_selector._get_unlocked_topics(db, 1)
            print(f"✓ Found {len(unlocked_topics)} unlocked topics")
            
            # Calculate topic scores
            topic_scores = await adaptive_question_selector._calculate_topic_scores(db, 1, unlocked_topics)
            
            print("\n--- Topic Scores (UCB Algorithm) ---")
            for topic in topic_scores:
                print(f"Topic: {topic['name']}")
                print(f"  UCB Score: {topic['ucb_score']:.3f}")
                print(f"  Interest Score: {topic['interest_score']:.3f}")
                print(f"  Base Reward: {topic['base_reward']:.3f}")
                print(f"  Confidence: {topic['confidence']:.3f}")
                print(f"  Exploration Bonus: {topic['exploration_bonus']:.3f}")
                print(f"  Questions Answered: {topic['questions_answered']}")
                print(f"  Total Questions: {topic['total_questions']}")
                print()
            
            # Test topic selection multiple times to see exploration vs exploitation
            print("--- Testing Exploration vs Exploitation ---")
            selections = {}
            for i in range(20):
                selected_topic = await adaptive_question_selector._select_topic_with_strategy(topic_scores)
                if selected_topic:
                    topic_name = selected_topic['name']
                    selections[topic_name] = selections.get(topic_name, 0) + 1
            
            print("Selection frequency over 20 trials:")
            for topic, count in selections.items():
                print(f"  {topic}: {count} times ({count/20*100:.1f}%)")
            
            return topic_scores
            
        except Exception as e:
            print(f"✗ Bandit algorithm test failed: {e}")
            return []

async def test_session_flow():
    """Test 6: Complete session flow"""
    print("\n=== Test 6: Complete Session Flow ===")
    
    async with AsyncSessionLocal() as db:
        try:
            print("Starting complete learning session...")
            
            # Start session
            session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id=1)
            session_id = session_data['session_id']
            print(f"✓ Session started: {session_id}")
            
            # Answer several questions
            for i in range(3):
                print(f"\n--- Question {i+1} ---")
                
                # Get question
                question_data = await adaptive_quiz_service.get_next_adaptive_question(db, session_id)
                
                if not question_data or "error" in question_data:
                    print(f"✗ No more questions available: {question_data}")
                    break
                
                print(f"Question: {question_data['question'][:100]}...")
                print(f"Topic: {question_data['topic_name']}")
                print(f"Difficulty: {question_data['difficulty']}")
                
                # Submit answer (simulate varying performance)
                action = "answer" if i < 2 else "teach_me"
                answer = "Option A" if i % 2 == 0 else "Option B"  # Mix correct/incorrect
                
                response = await adaptive_quiz_service.submit_adaptive_answer(
                    db=db,
                    quiz_question_id=question_data['quiz_question_id'],
                    user_answer=answer if action == "answer" else None,
                    time_spent=20 + i * 5,
                    action=action
                )
                
                print(f"Answer submitted: {action} - {response.get('correct', 'N/A')}")
                print(f"Session progress: {response['session_progress']['total_questions']} questions")
                
                # Check for discoveries
                if response.get('unlocked_topics'):
                    print(f"🎉 Unlocked topics: {response['unlocked_topics']}")
                if response.get('emerging_interests'):
                    print(f"💡 New interests: {response['emerging_interests']}")
            
            # Get final session state
            final_session = await db.execute(
                select(QuizSession).where(QuizSession.id == session_id)
            )
            session = final_session.scalar_one()
            
            print(f"\n✓ Session completed:")
            print(f"  Total questions: {session.total_questions}")
            print(f"  Correct answers: {session.correct_answers}")
            print(f"  Accuracy: {session.correct_answers/session.total_questions*100:.1f}%")
            
            return True
            
        except Exception as e:
            print(f"✗ Session flow test failed: {e}")
            return False

async def test_error_handling():
    """Test 7: Error handling scenarios"""
    print("\n=== Test 7: Error Handling ===")
    
    async with AsyncSessionLocal() as db:
        try:
            # Test with non-existent session
            print("--- Testing non-existent session ---")
            result = await adaptive_quiz_service.get_next_adaptive_question(db, session_id=99999)
            print(f"✓ Non-existent session handled: {result}")
            
            # Test with non-existent user
            print("--- Testing non-existent user ---")
            try:
                result = await adaptive_quiz_service.start_adaptive_session(db, user_id=99999)
                print(f"✓ Non-existent user handled: {result}")
            except Exception as e:
                print(f"✓ Expected error for non-existent user: {e}")
            
            # Test when no questions are available (remove all questions temporarily)
            print("--- Testing no available questions ---")
            
            # Create a user with no unlocked topics
            temp_user = User(
                id=999,
                email="temp@example.com", 
                username="tempuser",
                hashed_password="hashed",
                is_active=True
            )
            db.add(temp_user)
            await db.commit()
            
            session_data = await adaptive_quiz_service.start_adaptive_session(db, user_id=999)
            result = await adaptive_quiz_service.get_next_adaptive_question(db, session_data['session_id'])
            print(f"✓ No questions scenario handled: {result}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error handling test failed: {e}")
            return False

async def run_all_tests():
    """Run all tests in sequence"""
    print("🚀 Starting Comprehensive Adaptive Learning System Test")
    print("=" * 60)
    
    # Setup
    await setup_test_database()
    
    # Run tests
    test_results = {}
    
    test_results['database_state'] = await test_database_state()
    test_results['session_creation'] = await test_adaptive_session_creation()
    test_results['question_selection'] = await test_question_selection()
    test_results['answer_submission'] = await test_answer_submission()
    test_results['bandit_algorithm'] = await test_bandit_algorithm()
    test_results['session_flow'] = await test_session_flow()
    test_results['error_handling'] = await test_error_handling()
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    # Detailed findings
    print("\n📋 DETAILED FINDINGS:")
    
    if test_results['database_state']:
        db_state = test_results['database_state']
        print(f"• Database has {db_state['total_questions']} questions across {db_state['total_topics']} topics")
        print(f"• {db_state['valid_questions']} questions have valid options format")
        print(f"• User has {db_state['unlocked_topics']} unlocked topics")
    
    print(f"• Session creation: {'Working' if test_results['session_creation'] else 'Broken'}")
    print(f"• Question selection: {'Working' if test_results['question_selection'] else 'Broken'}")
    print(f"• Answer processing: {'Working' if test_results['answer_submission'] else 'Broken'}")
    print(f"• Multi-armed bandit: {'Working' if test_results['bandit_algorithm'] else 'Broken'}")
    print(f"• Complete session flow: {'Working' if test_results['session_flow'] else 'Broken'}")
    print(f"• Error handling: {'Working' if test_results['error_handling'] else 'Broken'}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_all_tests())