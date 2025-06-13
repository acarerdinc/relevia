#!/usr/bin/env python3
"""
Quick Gemini API status checker
Tests multiple calls to see if Gemini is slow or down
"""
import asyncio
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from services.gemini_service import gemini_service

async def test_gemini_multiple_times():
    """Test Gemini API multiple times to get average performance"""
    
    print("🤖 Testing Gemini API Performance...")
    print("=" * 40)
    
    test_prompts = [
        "What is AI? Answer in 5 words.",
        "Define machine learning briefly.",
        "What is deep learning?"
    ]
    
    results = []
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📡 Test {i}/3: {prompt[:30]}...")
        
        try:
            start_time = time.time()
            response = await gemini_service.generate_content(prompt)
            elapsed_ms = (time.time() - start_time) * 1000
            
            results.append(elapsed_ms)
            
            # Categorize response time
            if elapsed_ms < 1000:
                status = "🚀 FAST"
            elif elapsed_ms < 3000:
                status = "⚠️  SLOW"
            else:
                status = "🐌 VERY SLOW"
                
            print(f"   {status}: {elapsed_ms:.1f}ms")
            print(f"   Response: {response[:80]}{'...' if len(response) > 80 else ''}")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(None)
    
    # Calculate statistics
    valid_results = [r for r in results if r is not None]
    
    if valid_results:
        avg_time = sum(valid_results) / len(valid_results)
        min_time = min(valid_results)
        max_time = max(valid_results)
        
        print(f"\n📊 GEMINI PERFORMANCE SUMMARY:")
        print(f"   Average: {avg_time:.1f}ms")
        print(f"   Fastest: {min_time:.1f}ms")
        print(f"   Slowest: {max_time:.1f}ms")
        print(f"   Success: {len(valid_results)}/{len(test_prompts)}")
        
        # Overall assessment
        if avg_time < 1000:
            print(f"\n✅ VERDICT: Gemini is performing WELL")
        elif avg_time < 3000:
            print(f"\n⚠️  VERDICT: Gemini is SLOW - this could be causing question loading delays")
        else:
            print(f"\n🚨 VERDICT: Gemini is VERY SLOW - this is likely the bottleneck!")
            
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if avg_time > 2000:
            print(f"   • Enable fallback questions for better user experience")
            print(f"   • Consider reducing Gemini timeout to 5-8 seconds")
            print(f"   • Check Google Cloud status: https://status.cloud.google.com/")
        
        if len(valid_results) < len(test_prompts):
            print(f"   • Some Gemini calls failed - check API key and quota")
            
    else:
        print(f"\n❌ VERDICT: Gemini API is DOWN or misconfigured!")
        print(f"💡 Check:")
        print(f"   • API key is valid")
        print(f"   • Quota is not exceeded") 
        print(f"   • Network connectivity")

if __name__ == "__main__":
    asyncio.run(test_gemini_multiple_times())