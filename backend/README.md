# Relevia Backend - Dynamic AI Learning Ontology

A fully dynamic, AI-powered adaptive learning system that generates infinite topic trees based on user proficiency and interests.

## 🚀 Key Features

- **Infinite Ontology**: Starts with single "AI" topic, expands dynamically via Gemini AI
- **Proficiency-Based Unlocking**: New subtopics generated when users reach 60%+ accuracy
- **Interest Tracking**: 'Teach Me' (+0.2) and 'Skip' (-0.3) buttons track user preferences
- **Adaptive Difficulty**: Questions adapt to user skill level in real-time
- **Personalized Recommendations**: Topic suggestions based on interests and progress

## 📁 Project Structure

```
backend/
├── api/                    # FastAPI routes
│   ├── quiz.py            # Quiz endpoints
│   ├── topics.py          # Topic management
│   └── personalization.py # Interest & recommendations
├── services/              # Core business logic
│   ├── gemini_service.py         # AI question/topic generation
│   ├── quiz_service.py           # Adaptive quiz engine
│   ├── dynamic_ontology_service.py    # Interest tracking
│   └── dynamic_topic_generator.py     # AI topic creation
├── db/                    # Database layer
│   ├── models.py          # SQLAlchemy models
│   └── database.py        # Connection setup
├── scripts/               # Utilities
│   ├── setup/            # Database setup scripts
│   └── testing/          # Test utilities
└── tests/                # Test suites
    └── integration/      # End-to-end tests
```

## 🧪 Testing

### Setup Clean Environment
```bash
# Reset to minimal ontology (just AI root topic)
python scripts/setup/setup_minimal_dynamic_ontology.py
```

### Run End-to-End Test
```bash
# Comprehensive test of all features
python tests/integration/test_end_to_end.py
```

### Manual Testing Flow
```bash
# 1. Health check
curl http://localhost:8000/api/v1/health

# 2. Check initial progress (should show only AI topic)
curl http://localhost:8000/api/v1/personalization/progress/1

# 3. Start quiz
curl -X POST http://localhost:8000/api/v1/quiz/start \
  -H "Content-Type: application/json" \
  -d '{"topic_id": 195, "user_id": 1}'

# 4. Get question
curl http://localhost:8000/api/v1/quiz/question/{session_id}

# 5. Submit answer (triggers dynamic generation after 5+ correct)
curl -X POST http://localhost:8000/api/v1/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"quiz_question_id": X, "answer": "...", "action": "answer"}'

# 6. Test interest signals
# "teach_me" action
curl -X POST http://localhost:8000/api/v1/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"quiz_question_id": X, "answer": "", "action": "teach_me"}'

# "skip" action  
curl -X POST http://localhost:8000/api/v1/quiz/answer \
  -H "Content-Type: application/json" \
  -d '{"quiz_question_id": X, "answer": "", "action": "skip"}'
```

## 🎯 Expected Behavior

1. **Start**: Only "Artificial Intelligence" topic available
2. **Learn**: Answer questions to build proficiency (need 5+ questions, 60%+ accuracy)
3. **Expand**: AI generates 3 contextual subtopics when threshold reached
4. **Interest**: 'Teach Me' and 'Skip' buttons influence future topic generation
5. **Infinite**: Process repeats for every unlocked topic, creating infinite learning paths

## 🔧 Key Technical Fixes Applied

- ✅ Fixed database column type mismatch (`interest_signal` Float vs String)
- ✅ Added None checks for session counters (`total_questions`, `correct_answers`)
- ✅ Removed unreliable time-based interest inference
- ✅ Added proper error handling for AI generation failures
- ✅ Organized project structure with proper test folders

## 📊 Test Results

The end-to-end test demonstrates:
- ✅ Dynamic topic generation (3 new topics after 62.5% accuracy)
- ✅ Interest tracking ('Teach Me' and 'Skip' buttons working)
- ✅ Personalization endpoints (interests, recommendations, ontology)
- ✅ Adaptive quiz engine with real-time difficulty adjustment
- ✅ Complete database integration with all models