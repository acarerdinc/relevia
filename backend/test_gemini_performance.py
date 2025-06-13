#!/usr/bin/env python3
"""
Quick test script to diagnose Gemini API performance
"""
import asyncio
import time
from services.gemini_service import gemini_service

async def test_gemini_speed():
    """Test Gemini API response time"""
    
    print("🧪 Testing Gemini API Performance...")
    
    simple_prompt = """Generate a simple multiple choice question about artificial intelligence.

Format as JSON:
{
    "question": "What is AI?",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_answer": "Option 1",
    "explanation": "Simple explanation"
}"""
    
    try:
        # Test 1: Simple prompt
        start_time = time.time()
        print("📡 Sending simple test prompt to Gemini...")
        
        response = await gemini_service.generate_content(simple_prompt)
        
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"✅ Gemini responded in {elapsed_ms:.1f}ms")
        print(f"📝 Response length: {len(response)} characters")
        print(f"🔍 First 200 chars: {response[:200]}...")
        
        # Test 2: Check if it's a timeout issue
        if elapsed_ms > 5000:  # More than 5 seconds
            print("🐌 SLOW: Gemini API is taking more than 5 seconds!")
            print("💡 This explains the slow question loading.")
        elif elapsed_ms > 2000:  # More than 2 seconds
            print("⚠️  MODERATE: Gemini API is taking 2-5 seconds.")
            print("💡 This could be causing the perceived slowness.")
        else:
            print("🚀 FAST: Gemini API is responding quickly.")
            print("💡 The slowness might be elsewhere in the pipeline.")
            
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        print("💡 This could be why question loading is slow!")

if __name__ == "__main__":
    asyncio.run(test_gemini_speed())