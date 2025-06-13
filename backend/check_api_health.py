#!/usr/bin/env python3
"""
Quick API health checker - tests if our endpoints are responding
"""
import asyncio
import aiohttp
import time

async def check_api_health(base_url="http://localhost:8000"):
    """Check if API endpoints are healthy and responsive"""
    
    print("🌐 Testing API Endpoint Health...")
    print("=" * 40)
    
    # Key endpoints to test
    endpoints = [
        {
            "method": "GET",
            "path": "/api/v1/health/",
            "name": "Health Check",
            "expected_time": 100  # ms
        },
        {
            "method": "GET", 
            "path": "/api/v1/adaptive/dashboard/1",
            "name": "Dashboard",
            "expected_time": 500  # ms
        },
        {
            "method": "GET",
            "path": "/api/v1/adaptive/continue/1", 
            "name": "Continue Learning",
            "expected_time": 2000  # ms (can be slow due to question generation)
        }
    ]
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"\n📡 Testing {endpoint['name']}...")
            
            try:
                start_time = time.time()
                
                url = f"{base_url}{endpoint['path']}"
                async with session.request(endpoint['method'], url) as response:
                    data = await response.json()
                    
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Determine status
                if response.status == 200:
                    if elapsed_ms <= endpoint['expected_time']:
                        status = "✅ GOOD"
                    elif elapsed_ms <= endpoint['expected_time'] * 2:
                        status = "⚠️  SLOW"
                    else:
                        status = "🐌 VERY SLOW"
                else:
                    status = f"❌ HTTP {response.status}"
                
                print(f"   {status}: {elapsed_ms:.1f}ms")
                
                # Show relevant response data
                if 'error' in data:
                    print(f"   Error: {data['error']}")
                elif 'message' in data:
                    print(f"   Message: {data['message']}")
                elif 'session_id' in data:
                    print(f"   Session ID: {data['session_id']}")
                    
                results.append({
                    'endpoint': endpoint['name'],
                    'time_ms': elapsed_ms,
                    'status_code': response.status,
                    'healthy': response.status == 200 and elapsed_ms <= endpoint['expected_time'] * 2
                })
                
            except Exception as e:
                print(f"   ❌ CONNECTION ERROR: {e}")
                results.append({
                    'endpoint': endpoint['name'],
                    'error': str(e),
                    'healthy': False
                })
    
    # Summary
    print(f"\n📊 API HEALTH SUMMARY:")
    healthy_count = sum(1 for r in results if r.get('healthy', False))
    print(f"   Healthy endpoints: {healthy_count}/{len(results)}")
    
    if healthy_count == len(results):
        print(f"\n✅ VERDICT: All API endpoints are healthy!")
    elif healthy_count > 0:
        print(f"\n⚠️  VERDICT: Some endpoints have issues")
        for result in results:
            if not result.get('healthy', True):
                endpoint = result['endpoint']
                if 'error' in result:
                    print(f"   • {endpoint}: {result['error']}")
                else:
                    print(f"   • {endpoint}: Slow ({result.get('time_ms', 0):.1f}ms)")
    else:
        print(f"\n❌ VERDICT: API server may be down!")
        print(f"💡 Check:")
        print(f"   • Server is running on {base_url}")
        print(f"   • Database is connected")
        print(f"   • No port conflicts")

if __name__ == "__main__":
    asyncio.run(check_api_health())