"""
Test script to verify that question shuffling is working properly
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from services.quiz_service import quiz_engine

async def test_question_shuffling():
    """Test that questions are properly shuffled"""
    
    print("🧪 Testing question shuffling...")
    
    # Sample options and correct answer
    options = ["Paris", "London", "Berlin", "Madrid"]
    correct_answer = "Paris"
    
    # Test shuffling multiple times
    correct_positions = []
    
    for i in range(10):
        shuffled_options, shuffled_correct = quiz_engine._shuffle_question_options(options, correct_answer)
        
        # Find position of correct answer
        try:
            correct_pos = shuffled_options.index(shuffled_correct)
            correct_positions.append(correct_pos)
            print(f"Test {i+1}: Correct answer '{shuffled_correct}' at position {correct_pos} - {shuffled_options}")
        except ValueError:
            print(f"Test {i+1}: ERROR - Correct answer not found in options!")
            return False
    
    # Check if answers are distributed across different positions
    unique_positions = set(correct_positions)
    
    print(f"\n📊 Results:")
    print(f"   - Correct answer positions: {correct_positions}")
    print(f"   - Unique positions: {unique_positions}")
    print(f"   - Expected: Multiple positions (not always 0)")
    
    if len(unique_positions) > 1:
        print("✅ PASS: Questions are being shuffled properly!")
        return True
    else:
        print("❌ FAIL: Questions are not being shuffled (always same position)")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_question_shuffling())
    if result:
        print("\n🎉 Question shuffling is working correctly!")
    else:
        print("\n⚠️ Question shuffling needs further investigation.")