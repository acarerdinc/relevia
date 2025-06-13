# Relevia Backend Project Structure

## Overview
This is a FastAPI-based adaptive learning backend that provides personalized AI education through dynamic topic discovery and intelligent question selection.

## Directory Structure

```
backend/
├── README.md                  # Project documentation
├── PROJECT_STRUCTURE.md       # This file
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Production dependencies
├── requirements-simplified.txt # Minimal dependencies
├── docker-compose.yml         # Docker configuration
├── setup-guide.md            # Setup instructions
│
├── api/                       # API layer
│   ├── routes/               # Route definitions
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── health.py         # Health check endpoints
│   │   ├── personalization.py # User personalization APIs
│   │   ├── progress.py       # Progress tracking APIs
│   │   ├── quiz.py           # Traditional quiz APIs
│   │   ├── topic_requests.py # User-driven topic creation
│   │   └── topics.py         # Topic management APIs
│   │
│   └── v1/                   # API version 1
│       └── adaptive_learning.py # Main adaptive learning APIs
│
├── core/                     # Core configuration
│   ├── config.py            # Application configuration
│   └── logging_config.py    # Logging setup
│
├── db/                       # Database layer
│   ├── database.py          # Database connection
│   └── models.py            # SQLAlchemy models
│
├── services/                 # Business logic layer
│   ├── adaptive_interest_tracker.py    # Interest tracking
│   ├── adaptive_question_selector.py   # Question selection algorithm
│   ├── adaptive_quiz_service.py        # Main adaptive quiz service
│   ├── dynamic_ontology_builder.py     # User-driven topic creation
│   ├── dynamic_ontology_service.py     # Ontology management
│   ├── dynamic_topic_generator.py      # Topic generation
│   ├── gemini_service.py               # AI/LLM integration
│   └── quiz_service.py                 # Traditional quiz service
│
├── data/                     # Data definitions
│   ├── ai_ontology.py        # Basic AI topic structure
│   └── enhanced_ai_ontology.py # Enhanced topic definitions
│
├── scripts/                  # Utility scripts
│   ├── create_default_user.py # User setup
│   ├── reset_user_progress.py # Progress reset
│   ├── seed_ontology.py      # Database seeding
│   │
│   ├── migrations/           # Database migrations
│   │   └── add_adaptive_columns.py
│   │
│   ├── setup/               # Setup scripts
│   │   ├── add_dynamic_columns.py
│   │   ├── migrate_database.py
│   │   ├── reset_and_reseed.py
│   │   ├── reset_to_minimal_infinite.py
│   │   ├── seed_enhanced_ontology.py
│   │   └── setup_minimal_dynamic_ontology.py
│   │
│   ├── testing/             # Test utilities
│   │   └── test_dynamic_generation.py
│   │
│   └── utilities/           # General utilities
│       ├── quick-setup.sh
│       └── reset.sh
│
└── tests/                   # Test suites
    └── integration/         # Integration tests
        ├── test_direct_unlock.py
        ├── test_end_to_end.py
        ├── test_forced_proficiency.py
        ├── test_major_ai_domains.py
        ├── test_question_counter.py
        ├── test_quiz_error_fix.py
        └── test_quiz_improvements.py
```

## Key Components

### 🎯 **Adaptive Learning System**
- **adaptive_quiz_service.py**: Main service orchestrating the adaptive learning experience
- **adaptive_question_selector.py**: Multi-armed bandit algorithm for optimal question selection
- **adaptive_interest_tracker.py**: Tracks and learns user interests and preferences

### 🌳 **Dynamic Ontology**
- **dynamic_ontology_builder.py**: Creates topics based on user requests using AI
- **dynamic_ontology_service.py**: Manages the hierarchical topic structure
- **dynamic_topic_generator.py**: Generates new topics dynamically

### 🤖 **AI Integration**
- **gemini_service.py**: Google Gemini AI integration for question generation and topic interpretation

### 📊 **APIs**
- **Adaptive Learning**: `/api/v1/adaptive/*` - Main adaptive learning endpoints
- **Topic Management**: `/api/v1/topics/*` - Topic CRUD and user-driven creation
- **Quiz System**: `/api/v1/quiz/*` - Traditional quiz functionality
- **Progress Tracking**: `/api/v1/progress/*` - User progress and analytics

### 🗃️ **Database**
- **models.py**: Complete database schema with adaptive learning tables
- **database.py**: AsyncSession configuration for PostgreSQL

## Architecture Principles

1. **🎯 Adaptive Learning**: Multi-armed bandit algorithm balances exploration/exploitation
2. **🌱 Dynamic Growth**: Topics are created based on user interest and AI analysis
3. **🔄 Infinite Learning**: System expands indefinitely based on user progress
4. **🤖 AI-Powered**: Uses Google Gemini for question generation and semantic analysis
5. **📈 Data-Driven**: All decisions based on user interaction data and progress metrics

## Recent Improvements

- ✅ **Fixed LLM Topic Assignment**: Now correctly detects and assigns to existing LLM topics
- ✅ **Enhanced Semantic Matching**: Improved AI prompt for better topic hierarchy
- ✅ **Duplicate Prevention**: Fixed question repetition within sessions
- ✅ **4-Option Validation**: Ensures all questions have exactly 4 options
- ✅ **Cleaned Project Structure**: Removed temporary scripts and organized hierarchy