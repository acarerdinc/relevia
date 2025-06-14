import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import the FastAPI app
from main import app
from fastapi import Request
from fastapi.responses import JSONResponse

# Add CORS headers to all responses for Vercel
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    # Handle preflight
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "https://relevia.vercel.app",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://relevia.vercel.app"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


# Export the FastAPI app for Vercel
# Vercel will automatically detect this as an ASGI application