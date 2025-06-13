#!/usr/bin/env python3
"""
Performance diagnostic tool for Relevia backend
Tests API endpoints, Gemini API, and database performance
"""
import asyncio
import aiohttp
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from core.logging_config import logger
from services.gemini_service import gemini_service
from db.database import AsyncSessionLocal
from db.models import Topic
from sqlalchemy import select

class PerformanceDiagnostic:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    async def run_full_diagnostic(self):
        """Run comprehensive performance diagnostic"""
        print("🔍 Starting Performance Diagnostic...")
        print("=" * 50)
        
        # Test 1: Database Performance
        await self.test_database_performance()
        
        # Test 2: Gemini API Performance
        await self.test_gemini_performance()
        
        # Test 3: API Endpoints Performance
        await self.test_api_endpoints()
        
        # Test 4: Question Generation Pipeline
        await self.test_question_generation_pipeline()
        
        # Generate summary
        self.print_diagnostic_summary()
    
    async def test_database_performance(self):
        """Test database query performance"""
        print("\n📊 Testing Database Performance...")
        
        try:
            start_time = time.time()
            async with AsyncSessionLocal() as session:
                # Simple query
                result = await session.execute(select(Topic))
                topics = result.scalars().all()
                
            db_time = (time.time() - start_time) * 1000
            
            self.results['database'] = {
                'response_time_ms': db_time,
                'status': 'healthy' if db_time < 100 else 'slow' if db_time < 500 else 'critical',
                'topics_found': len(topics)
            }
            
            print(f"   ✅ Database query: {db_time:.1f}ms ({len(topics)} topics)")
            
        except Exception as e:
            self.results['database'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"   ❌ Database error: {e}")
    
    async def test_gemini_performance(self):
        """Test Gemini API performance directly"""
        print("\n🤖 Testing Gemini API Performance...")
        
        simple_prompt = "Generate a simple question about AI. Return only: What is AI?"
        
        try:
            start_time = time.time()
            response = await gemini_service.generate_content(simple_prompt)
            gemini_time = (time.time() - start_time) * 1000
            
            self.results['gemini'] = {
                'response_time_ms': gemini_time,
                'status': 'fast' if gemini_time < 1000 else 'slow' if gemini_time < 5000 else 'critical',
                'response_length': len(response) if response else 0,
                'success': bool(response)
            }
            
            status_emoji = "🚀" if gemini_time < 1000 else "⚠️" if gemini_time < 5000 else "🐌"
            print(f"   {status_emoji} Gemini API: {gemini_time:.1f}ms ({len(response) if response else 0} chars)")
            
        except Exception as e:
            self.results['gemini'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"   ❌ Gemini error: {e}")
    
    async def test_api_endpoints(self):
        """Test key API endpoints"""
        print("\n🌐 Testing API Endpoints...")
        
        endpoints = [
            ("GET", "/api/v1/health/", "Health check"),
            ("GET", "/api/v1/adaptive/dashboard/1", "Dashboard"),
            ("GET", "/api/v1/adaptive/continue/1", "Continue learning"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for method, path, description in endpoints:
                try:
                    start_time = time.time()
                    
                    if method == "GET":
                        async with session.get(f"{self.base_url}{path}") as response:
                            data = await response.json()
                            
                    api_time = (time.time() - start_time) * 1000
                    
                    status = 'fast' if api_time < 500 else 'slow' if api_time < 2000 else 'critical'
                    status_emoji = "✅" if api_time < 500 else "⚠️" if api_time < 2000 else "❌"
                    
                    self.results[f'api_{path.replace("/", "_")}'] = {
                        'response_time_ms': api_time,
                        'status': status,
                        'http_status': response.status
                    }
                    
                    print(f"   {status_emoji} {description}: {api_time:.1f}ms (HTTP {response.status})")
                    
                except Exception as e:
                    self.results[f'api_{path.replace("/", "_")}'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    print(f"   ❌ {description}: {e}")
    
    async def test_question_generation_pipeline(self):
        """Test the full question generation pipeline"""
        print("\n⚡ Testing Question Generation Pipeline...")
        
        try:
            # Test the adaptive question selector directly
            from services.adaptive_question_selector import adaptive_question_selector
            from db.database import AsyncSessionLocal
            
            start_time = time.time()
            
            async with AsyncSessionLocal() as session:
                question_data = await adaptive_question_selector.select_next_question(
                    session, user_id=1, current_session_id=None
                )
                
            pipeline_time = (time.time() - start_time) * 1000
            
            self.results['question_pipeline'] = {
                'response_time_ms': pipeline_time,
                'status': 'fast' if pipeline_time < 1000 else 'slow' if pipeline_time < 5000 else 'critical',
                'question_found': bool(question_data and 'error' not in question_data),
                'strategy': question_data.get('selection_strategy', 'unknown') if question_data else None
            }
            
            status_emoji = "🚀" if pipeline_time < 1000 else "⚠️" if pipeline_time < 5000 else "🐌"
            strategy = question_data.get('selection_strategy', 'unknown') if question_data else 'failed'
            
            print(f"   {status_emoji} Question pipeline: {pipeline_time:.1f}ms (strategy: {strategy})")
            
        except Exception as e:
            self.results['question_pipeline'] = {
                'status': 'error',
                'error': str(e)
            }
            print(f"   ❌ Pipeline error: {e}")
    
    def print_diagnostic_summary(self):
        """Print diagnostic summary and recommendations"""
        print("\n" + "=" * 50)
        print("📋 DIAGNOSTIC SUMMARY")
        print("=" * 50)
        
        # Overall assessment
        critical_issues = []
        slow_components = []
        
        for component, data in self.results.items():
            if data.get('status') == 'error':
                critical_issues.append(f"{component}: {data.get('error', 'Unknown error')}")
            elif data.get('status') == 'critical':
                critical_issues.append(f"{component}: Very slow ({data.get('response_time_ms', 0):.1f}ms)")
            elif data.get('status') == 'slow':
                slow_components.append(f"{component}: Slow ({data.get('response_time_ms', 0):.1f}ms)")
        
        # Print issues
        if critical_issues:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in critical_issues:
                print(f"   • {issue}")
        
        if slow_components:
            print("\n⚠️  SLOW COMPONENTS:")
            for component in slow_components:
                print(f"   • {component}")
        
        if not critical_issues and not slow_components:
            print("\n✅ All systems performing well!")
        
        # Specific recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        gemini_data = self.results.get('gemini', {})
        if gemini_data.get('status') in ['slow', 'critical']:
            print("   • Gemini API is slow - consider enabling fallback questions")
            print("   • Check Gemini API status at https://status.cloud.google.com/")
        
        db_data = self.results.get('database', {})
        if db_data.get('status') in ['slow', 'critical']:
            print("   • Database is slow - check Docker container resources")
            print("   • Consider adding database indexes")
        
        pipeline_data = self.results.get('question_pipeline', {})
        if pipeline_data.get('strategy') == 'fallback':
            print("   • System is using fallback questions - check question pool")
        
        # Performance baseline
        print("\n📊 PERFORMANCE BASELINES:")
        print("   • Database queries: <100ms (good), <500ms (acceptable)")
        print("   • Gemini API calls: <1s (good), <5s (acceptable)")
        print("   • API endpoints: <500ms (good), <2s (acceptable)")
        print("   • Question pipeline: <1s (good), <5s (acceptable)")

async def main():
    """Run diagnostic"""
    diagnostic = PerformanceDiagnostic()
    await diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())