#!/bin/bash

echo "🚀 Relevia Backend Quick Setup"
echo "============================"

# Check if Docker is installed
if command -v docker &> /dev/null; then
    echo "✅ Docker found. Starting PostgreSQL and Redis..."
    
    # Start services with docker-compose
    docker-compose up -d
    
    echo "⏳ Waiting for services to be ready..."
    sleep 5
    
    echo "✅ PostgreSQL and Redis are running!"
else
    echo "❌ Docker not found. Please install Docker or set up PostgreSQL and Redis manually."
    echo "See setup-guide.md for manual installation instructions."
    exit 1
fi

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "✅ Python $python_version is installed"
else
    echo "❌ Python 3.11+ is required. You have Python $python_version"
    exit 1
fi

# Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for Gemini API key
echo ""
if grep -q "GEMINI_API_KEY=$" .env; then
    echo "⚠️  IMPORTANT: You need to add your Gemini API key to .env"
    echo "   1. Go to https://makersuite.google.com/app/apikey"
    echo "   2. Get your API key"
    echo "   3. Add it to the GEMINI_API_KEY line in .env"
else
    echo "✅ Gemini API key found in .env"
fi

echo ""
echo "🎉 Setup complete! Next steps:"
echo "   1. Make sure you've added your Gemini API key to .env"
echo "   2. Run: source venv/bin/activate"
echo "   3. Run: python scripts/seed_ontology.py"
echo "   4. Run: python main.py"
echo ""
echo "The API will be available at http://localhost:8000"