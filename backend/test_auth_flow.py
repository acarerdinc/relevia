#!/usr/bin/env python3
"""Test the complete authentication flow."""

import asyncio
import httpx
from core.config import settings

async def test_auth_flow():
    """Test login and /me endpoint."""
    base_url = "http://localhost:8000/api/v1"
    
    # Test credentials
    email = "test@relevia.ai"
    password = "securepassword"
    
    async with httpx.AsyncClient() as client:
        print("1. Testing login endpoint...")
        login_data = {
            "username": email,  # OAuth2 expects 'username' field
            "password": password
        }
        
        try:
            response = await client.post(
                f"{base_url}/auth/login",
                data=login_data,  # Use form data, not JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            print(f"Login response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"Login successful! Token: {token_data['access_token'][:50]}...")
                
                # Test /me endpoint
                print("\n2. Testing /me endpoint...")
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                me_response = await client.get(f"{base_url}/auth/me", headers=headers)
                
                print(f"/me response status: {me_response.status_code}")
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"User data: {user_data}")
                else:
                    print(f"Error: {me_response.text}")
            else:
                print(f"Login failed: {response.text}")
                
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    print(f"Using SECRET_KEY: {settings.SECRET_KEY[:20]}...")
    print(f"Testing against backend...\n")
    asyncio.run(test_auth_flow())