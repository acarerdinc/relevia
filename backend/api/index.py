import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import the FastAPI app
from main import app

# Export the FastAPI app for Vercel
# Vercel will automatically detect this as an ASGI application