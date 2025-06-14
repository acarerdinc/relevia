"""
Test login directly
"""
import asyncio
import httpx
import sys

async def test_login():
    # Use the production URL if provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    login_data = {
        "username": "info@acarerdinc.com",  # OAuth2 form uses 'username' field
        "password": "fenapass1"
    }
    
    async with httpx.AsyncClient() as client:
        # Test login
        print(f"Testing login at {base_url}/api/v1/auth/login")
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            data=login_data  # Use form data, not JSON
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"\nToken received: {token[:20]}...")
            
            # Test /me endpoint
            print(f"\nTesting /me endpoint...")
            headers = {"Authorization": f"Bearer {token}"}
            me_response = await client.get(
                f"{base_url}/api/v1/auth/me",
                headers=headers
            )
            print(f"Status: {me_response.status_code}")
            print(f"Response: {me_response.text}")

if __name__ == "__main__":
    asyncio.run(test_login())