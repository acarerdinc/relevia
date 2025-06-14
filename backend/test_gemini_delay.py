#!/usr/bin/env python3
"""
Test script to measure Gemini API delay for question generation.
Mimics the actual question generation process used in the system.
"""
import asyncio
import time
import json
import statistics
from typing import List, Dict, Tuple
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.gemini_service import GeminiService
from core.config import settings
from core.logging_config import logger


class GeminiDelayTester:
    def __init__(self):
        self.gemini_service = GeminiService()
        self.results = []
        
    async def measure_question_generation(self, topic: str, difficulty: int, mastery_level: str = "novice") -> Tuple[float, bool, str]:
        """
        Measure the time it takes to generate a single question.
        Returns: (delay_seconds, success, error_message)
        """
        start_time = time.time()
        error_msg = ""
        success = False
        
        try:
            # Mimic actual question generation parameters
            # Note: generate_question doesn't take mastery_level, but we can include it in context
            context = {
                "mastery_level": mastery_level,
                "previous_questions": []
            }
            question = await self.gemini_service.generate_question(
                topic=topic,
                difficulty=difficulty,
                context=context
            )
            
            # Validate the response has expected structure
            if question and all(key in question for key in ['question', 'options', 'correct_answer', 'explanation']):
                success = True
            else:
                error_msg = "Invalid question structure"
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Question generation failed: {e}")
        
        delay = time.time() - start_time
        return delay, success, error_msg
    
    async def run_batch_test(self, num_tests: int = 10, topics: List[str] = None, difficulties: List[int] = None):
        """Run multiple tests and collect statistics."""
        if topics is None:
            topics = [
                "Machine Learning",
                "Neural Networks", 
                "Computer Vision",
                "Natural Language Processing",
                "Reinforcement Learning"
            ]
        
        if difficulties is None:
            difficulties = [1, 3, 5, 7, 9]  # Various difficulty levels
        
        mastery_levels = ["novice", "competent", "proficient", "expert", "master"]
        
        print(f"\n{'='*60}")
        print(f"GEMINI API DELAY TEST - Question Generation")
        print(f"{'='*60}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Number of tests: {num_tests}")
        print(f"Topics: {', '.join(topics)}")
        print(f"Difficulties: {difficulties}")
        print(f"Mastery levels: {', '.join(mastery_levels)}")
        print(f"{'='*60}\n")
        
        successful_delays = []
        failed_count = 0
        
        for i in range(num_tests):
            # Rotate through topics, difficulties, and mastery levels
            topic = topics[i % len(topics)]
            difficulty = difficulties[i % len(difficulties)]
            mastery = mastery_levels[i % len(mastery_levels)]
            
            print(f"Test {i+1}/{num_tests}: {topic} (Difficulty: {difficulty}, Mastery: {mastery}) - ", end='', flush=True)
            
            delay, success, error = await self.measure_question_generation(topic, difficulty, mastery)
            
            result = {
                'test_num': i + 1,
                'topic': topic,
                'difficulty': difficulty,
                'mastery_level': mastery,
                'delay': delay,
                'success': success,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            self.results.append(result)
            
            if success:
                successful_delays.append(delay)
                print(f"✓ {delay:.2f}s")
            else:
                failed_count += 1
                print(f"✗ Failed after {delay:.2f}s - {error}")
            
            # Small delay between requests to avoid rate limiting
            if i < num_tests - 1:
                await asyncio.sleep(0.5)
        
        # Calculate statistics
        print(f"\n{'='*60}")
        print("RESULTS SUMMARY")
        print(f"{'='*60}")
        
        if successful_delays:
            print(f"Successful requests: {len(successful_delays)}/{num_tests}")
            print(f"Failed requests: {failed_count}/{num_tests}")
            print(f"\nDelay Statistics (successful requests only):")
            print(f"  - Min: {min(successful_delays):.2f}s")
            print(f"  - Max: {max(successful_delays):.2f}s")
            print(f"  - Mean: {statistics.mean(successful_delays):.2f}s")
            print(f"  - Median: {statistics.median(successful_delays):.2f}s")
            if len(successful_delays) > 1:
                print(f"  - Std Dev: {statistics.stdev(successful_delays):.2f}s")
            
            # Performance breakdown
            print(f"\nPerformance Breakdown:")
            under_1s = sum(1 for d in successful_delays if d < 1)
            under_3s = sum(1 for d in successful_delays if d < 3)
            under_5s = sum(1 for d in successful_delays if d < 5)
            over_5s = sum(1 for d in successful_delays if d >= 5)
            
            print(f"  - Under 1s: {under_1s} ({under_1s/len(successful_delays)*100:.1f}%)")
            print(f"  - Under 3s: {under_3s} ({under_3s/len(successful_delays)*100:.1f}%)")
            print(f"  - Under 5s: {under_5s} ({under_5s/len(successful_delays)*100:.1f}%)")
            print(f"  - Over 5s: {over_5s} ({over_5s/len(successful_delays)*100:.1f}%)")
        else:
            print(f"All {num_tests} requests failed!")
        
        # Save detailed results
        results_file = f"gemini_delay_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': num_tests,
                    'successful': len(successful_delays),
                    'failed': failed_count,
                    'mean_delay': statistics.mean(successful_delays) if successful_delays else None,
                    'median_delay': statistics.median(successful_delays) if successful_delays else None,
                    'min_delay': min(successful_delays) if successful_delays else None,
                    'max_delay': max(successful_delays) if successful_delays else None,
                },
                'detailed_results': self.results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        print(f"{'='*60}\n")
        
    async def test_concurrent_requests(self, num_concurrent: int = 5):
        """Test concurrent request handling."""
        print(f"\n{'='*60}")
        print(f"CONCURRENT REQUEST TEST ({num_concurrent} simultaneous requests)")
        print(f"{'='*60}\n")
        
        topics = ["Machine Learning", "Neural Networks", "Computer Vision", "NLP", "Reinforcement Learning"]
        
        # Create concurrent tasks
        tasks = []
        for i in range(num_concurrent):
            topic = topics[i % len(topics)]
            difficulty = (i % 10) + 1
            tasks.append(self.measure_question_generation(topic, difficulty))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        successful = sum(1 for _, success, _ in results if success)
        individual_times = [delay for delay, success, _ in results if success]
        
        print(f"Total time for {num_concurrent} concurrent requests: {total_time:.2f}s")
        print(f"Successful: {successful}/{num_concurrent}")
        if individual_times:
            print(f"Average individual delay: {statistics.mean(individual_times):.2f}s")
            print(f"Speedup factor: {statistics.mean(individual_times) * num_concurrent / total_time:.2f}x")
        
        print("\nIndividual request times:")
        for i, (delay, success, error) in enumerate(results):
            status = "✓" if success else "✗"
            print(f"  Request {i+1}: {status} {delay:.2f}s" + (f" - {error}" if error else ""))


async def main():
    """Main test runner."""
    tester = GeminiDelayTester()
    
    # Check if Gemini API key is configured
    if not settings.GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not found in settings!")
        print("Please set the GEMINI_API_KEY environment variable.")
        return
    
    # Run different test scenarios
    try:
        # Test 1: Basic delay measurement
        await tester.run_batch_test(num_tests=20)
        
        # Test 2: Concurrent requests
        await tester.test_concurrent_requests(num_concurrent=5)
        
        # Test 3: High difficulty questions (typically take longer)
        print(f"\n{'='*60}")
        print("HIGH DIFFICULTY TEST")
        print(f"{'='*60}")
        await tester.run_batch_test(
            num_tests=5,
            topics=["Advanced Machine Learning Theory", "Quantum Computing"],
            difficulties=[8, 9, 10]
        )
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        print(f"\nTest failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(main())