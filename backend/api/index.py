import sys
import os
from pathlib import Path

try:
    # Add the backend directory to Python path
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(backend_dir))
    
    # Set environment variable for Vercel
    os.environ['VERCEL'] = '1'
    
    # Import the FastAPI app
    from main import app
    
    # Export the FastAPI app for Vercel
    # Vercel will automatically detect this as an ASGI application
    
except Exception as e:
    import traceback
    print(f"Error importing app: {e}")
    print(f"Traceback: {traceback.format_exc()}")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Directory contents: {os.listdir('.')}")
    raise