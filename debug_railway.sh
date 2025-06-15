#!/bin/bash

# Railway debugging script
echo "=== Railway Deployment Debug ==="

# Check if railway CLI is installed
if command -v railway &> /dev/null; then
    echo "✓ Railway CLI found"
    
    # Get logs
    echo -e "\n=== Recent Logs ==="
    railway logs --last 50 > railway_debug_logs.txt
    echo "Logs saved to railway_debug_logs.txt"
    
    # Get deployment status
    echo -e "\n=== Deployment Status ==="
    railway status
    
    # Get environment info
    echo -e "\n=== Environment Variables (names only) ==="
    railway variables --json | jq -r 'keys[]' 2>/dev/null || echo "Could not list variables"
else
    echo "❌ Railway CLI not installed"
    echo "Install with: npm install -g @railway/cli"
fi

# Common deployment issues to check
echo -e "\n=== Checking Common Issues ==="

# Check Python version
echo -n "1. Python version in nixpacks.toml: "
grep PYTHON_VERSION nixpacks.toml 2>/dev/null || echo "Not specified"

# Check if requirements.txt exists
echo -n "2. Requirements file: "
if [ -f "backend/requirements.txt" ]; then
    echo "✓ Found"
    echo "   First 5 dependencies:"
    head -5 backend/requirements.txt | sed 's/^/   /'
else
    echo "❌ Not found at backend/requirements.txt"
fi

# Check start command
echo -n "3. Start command in Procfile: "
cat Procfile 2>/dev/null || echo "Not found"

# Check main.py exists
echo -n "4. Main app file: "
if [ -f "backend/main.py" ]; then
    echo "✓ Found"
else
    echo "❌ Not found at backend/main.py"
fi

echo -e "\n=== Quick Fixes to Try ==="
echo "1. If 'module not found': Check requirements.txt has all dependencies"
echo "2. If 'no module named main': Ensure backend/main.py exists"
echo "3. If 'port binding': Railway sets PORT env var automatically"
echo "4. If 'build failed': Check Python version compatibility"