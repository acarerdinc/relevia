import asyncio
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health endpoint
try:
    response = client.get('/api/v1/health')
    print(f'Health check: {response.status_code} - {response.json()}')
except Exception as e:
    print(f'Health check failed: {e}')

# Test progress endpoint
try:
    response = client.get('/api/v1/progress/user/1')
    print(f'Progress endpoint: {response.status_code}')
    if response.status_code != 200:
        print(f'Error: {response.text[:500]}')
    else:
        print('Progress endpoint working')
except Exception as e:
    print(f'Progress endpoint failed: {e}')

# Test adaptive dashboard
try:
    response = client.get('/api/v1/adaptive/dashboard/1')
    print(f'Dashboard endpoint: {response.status_code}')
    if response.status_code != 200:
        print(f'Error: {response.text[:500]}')
    else:
        print('Dashboard endpoint working')
except Exception as e:
    print(f'Dashboard endpoint failed: {e}')