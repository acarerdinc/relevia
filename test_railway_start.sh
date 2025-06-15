#!/bin/bash

echo "=== Testing Railway Start Command ==="

# Save current directory
ORIGINAL_DIR=$(pwd)

# Test if we can start the app
echo "Testing start command..."
cd backend

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ ERROR: main.py not found in backend directory"
    echo "Files in backend:"
    ls -la | grep "\.py$"
    cd $ORIGINAL_DIR
    exit 1
fi

# Try to import main
echo "Testing Python import..."
python -c "import main; print('✓ main.py imports successfully')" 2>&1

# Check for app object
echo "Checking for FastAPI app..."
python -c "from main import app; print('✓ FastAPI app found')" 2>&1

# Return to original directory
cd $ORIGINAL_DIR

echo -e "\n=== Common Railway Deployment Errors ==="
echo "1. 'ModuleNotFoundError': Missing dependency in requirements.txt"
echo "2. 'No module named main': Wrong directory structure"
echo "3. 'Address already in use': PORT env var issue"
echo "4. 'Connection refused': Database URL not set"

echo -e "\n=== What error are you seeing? ==="
echo "Please describe the error message or where deployment fails"