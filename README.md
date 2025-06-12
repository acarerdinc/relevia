# 🧠 Relevia - Adaptive AI Learning Platform

An intelligent learning platform that uses **Multi-Armed Bandit algorithms** and **dynamic ontology expansion** to create personalized, infinite learning experiences. The system adapts to user interests and proficiency levels, automatically generating questions and unlocking specialized topics.

## 🌟 Key Features

### 🎯 **Adaptive Learning Algorithm**
- **Multi-Armed Bandit (UCB)** for intelligent topic selection
- **Exploration vs Exploitation** (20% exploration, 80% exploitation)
- **Dynamic difficulty scaling** based on topic depth and user skill
- **Interest tracking** with cross-topic inference

### 🌳 **Infinite Dynamic Ontology**
- **Starts with single AI root topic**
- **Auto-generates subtopics** based on user proficiency and interest
- **True infinite tree structure** - no predefined limits
- **Meaningful progression** requiring demonstrated understanding

### 🔄 **Session Continuity**
- **Remembers where you left off** across sessions
- **Strong recency bias** to continue from last topic
- **Progress tracking** with visual feedback
- **Unlock thresholds** clearly displayed

### 📊 **Real-time Progress Visualization**
- **Proficiency bars** showing current accuracy vs required thresholds
- **Interest level tracking** based on user actions
- **Unlock progress** indicators for next level
- **Topic specialization** status and guidance

## 🏗️ Architecture

### Backend (Python FastAPI)
```
backend/
├── api/v1/              # REST API endpoints
├── services/            # Core business logic
│   ├── adaptive_question_selector.py    # Multi-Armed Bandit algorithm
│   ├── adaptive_interest_tracker.py     # Interest inference engine
│   ├── adaptive_quiz_service.py         # Main service orchestrator
│   ├── dynamic_ontology_service.py      # Topic unlocking logic
│   └── gemini_service.py                # AI question generation
├── db/                  # Database models and connection
└── core/                # Configuration and utilities
```

### Frontend (Next.js + TypeScript)
```
frontend/
├── src/
│   ├── components/
│   │   ├── AdaptiveLearning.tsx         # Main learning interface
│   │   ├── QuizInterface.tsx            # Question display
│   │   └── ProgressDashboard.tsx        # Analytics dashboard
│   └── app/             # Next.js app router
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- PostgreSQL
- Google Gemini API key

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/relevia"
export GEMINI_API_KEY="your_gemini_api_key"

# Initialize database
python scripts/setup/reset_and_reseed.py

# Start server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

**Backend (.env)**
```env
DATABASE_URL=postgresql://user:password@localhost/relevia_db
GEMINI_API_KEY=your_google_gemini_api_key
ENVIRONMENT=development
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📈 How It Works

### 1. **Adaptive Question Selection**
- Uses **Upper Confidence Bound (UCB)** algorithm
- Balances exploration of new topics vs exploitation of engaging ones
- Factors: interest score, proficiency, recency, specialization bonus

### 2. **Interest Tracking**
- **Correct answers**: +0.45 interest boost
- **"Teach Me"**: +0.15 (interested but struggling)
- **Skip**: -0.4 (strong negative signal)
- **No time-based penalties**

### 3. **Topic Unlocking**
- **Proficiency threshold**: 60% accuracy
- **Minimum questions**: 3 per topic
- **Interest requirement**: 40%+ interest level
- **Automatic generation** of 5-7 subtopics

### 4. **Progression Example**
```
Artificial Intelligence (Root)
├── Machine Learning Algorithms
│   ├── Supervised Learning
│   │   ├── Decision Trees
│   │   └── Neural Networks
│   └── Unsupervised Learning
├── Natural Language Processing
└── Computer Vision
```

## 🎮 User Experience

### Learning Flow
1. **Start**: Begin with AI fundamentals
2. **Progress**: Answer questions, get feedback
3. **Unlock**: Meet proficiency thresholds to unlock specialized topics
4. **Specialize**: System automatically moves to subtopics
5. **Continue**: Resume exactly where you left off

### Visual Feedback
- **Progress bars** show proficiency and interest levels
- **Unlock indicators** show proximity to next level
- **Topic status** explains current learning phase
- **No infinite scrolling** - progress bars at bottom

## 🔬 Technical Implementation

### Multi-Armed Bandit Algorithm
```python
# UCB Score Calculation
ucb_score = base_reward + confidence_interval

base_reward = (
    0.4 * interest_score +           # User engagement
    0.3 * proficiency_score +        # Current skill level  
    0.3 * exploration_bonus +        # Discovery incentive
    0.3 * specialization_bonus +     # Depth preference
    0.4 * recency_bonus             # Session continuity
)

confidence = 2.0 * sqrt(log(total_selections) / topic_selections)
```

### Interest Update Logic
```python
# Direct signal-based updates (no decay)
if signal > 0:
    interest_score = min(1.0, interest_score + signal * 0.2)
else:
    interest_score = max(0.0, interest_score + signal * 0.2)
```

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest tests/

# Test specific components
python test_adaptive_system.py
python scripts/testing/test_dynamic_generation.py

# Frontend tests
cd frontend
npm test
```

## 🛠️ Development

### Adding New Topics
Topics are generated dynamically, but you can customize the generation prompts in:
- `services/dynamic_topic_generator.py`
- `services/gemini_service.py`

### Tuning Algorithm Parameters
Key parameters in `services/adaptive_question_selector.py`:
```python
self.exploration_rate = 0.2           # 20% exploration
self.confidence_multiplier = 2.0      # UCB confidence
self.interest_weight = 0.4            # Interest importance
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Multi-Armed Bandit algorithms** for intelligent content selection
- **Google Gemini** for dynamic question generation
- **FastAPI** and **Next.js** for robust full-stack architecture
- **PostgreSQL** for reliable data persistence

---

**Built with ❤️ for personalized, adaptive learning experiences**