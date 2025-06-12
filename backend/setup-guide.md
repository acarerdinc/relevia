# Backend Setup Guide

## 1. PostgreSQL Setup

### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Create a database and user
psql postgres
```

In the PostgreSQL prompt:
```sql
CREATE DATABASE relevia;
CREATE USER releviauser WITH ENCRYPTED PASSWORD 'releviapass123';
GRANT ALL PRIVILEGES ON DATABASE relevia TO releviauser;
\q
```

### Alternative: Use Docker
```bash
docker run --name relevia-postgres -e POSTGRES_USER=releviauser -e POSTGRES_PASSWORD=releviapass123 -e POSTGRES_DB=relevia -p 5432:5432 -d postgres:15
```

## 2. Redis Setup

### macOS (using Homebrew)
```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis
```

### Alternative: Use Docker
```bash
docker run --name relevia-redis -p 6379:6379 -d redis:7-alpine
```

## 3. Get a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key
4. Copy the key for your .env file

## 4. Pinecone Setup (Optional for MVP)

1. Go to [Pinecone](https://www.pinecone.io/)
2. Sign up for a free account
3. Create a new index named "relevia-skills"
4. Get your API key from the dashboard

Note: Pinecone is optional for the MVP. You can skip this initially.

## 5. Create Your .env File

Create `/Users/acar/projects/relevia/backend/.env` with:

```env
# Database
DATABASE_URL=postgresql://releviauser:releviapass123@localhost/relevia

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key-here

# Pinecone (optional for MVP)
PINECONE_API_KEY=your-pinecone-key-or-leave-empty
PINECONE_INDEX=relevia-skills

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## 6. Python Virtual Environment

```bash
cd /Users/acar/projects/relevia/backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## 7. Initialize the Database

```bash
# Make sure you're in the backend directory with venv activated
cd /Users/acar/projects/relevia/backend
python scripts/seed_ontology.py
```

## 8. Run the Backend

```bash
python main.py
```

The API will be available at http://localhost:8000
API docs at http://localhost:8000/docs

## Troubleshooting

### PostgreSQL Connection Issues
- Make sure PostgreSQL is running: `brew services list`
- Check if you can connect: `psql -U releviauser -d relevia`

### Redis Connection Issues
- Check if Redis is running: `redis-cli ping` (should return PONG)

### Python Package Issues
- Make sure you're using Python 3.11+: `python --version`
- If packages fail to install, try: `pip install --upgrade pip`

## Quick Test

Once everything is set up, test the API:
```bash
curl http://localhost:8000/api/v1/health
```

Should return: `{"status":"healthy","service":"relevia-api"}`