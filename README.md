# 🧠 Relevia - Adaptive AI Learning Platform

An intelligent learning platform that uses **Multi-Armed Bandit algorithms** and **dynamic ontology expansion** to create personalized, infinite learning experiences. The system adapts to user interests and proficiency levels, automatically generating questions and unlocking specialized topics.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+

### Clone and Run

```bash
# Clone the repository
git clone <repository-url>
cd relevia

# Backend setup
cd backend
pip install -r requirements.txt
echo "DATABASE_URL=sqlite+aiosqlite:///./relevia.db" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env
uvicorn main:app --port 8001 --host 0.0.0.0 --reload

# Frontend setup (new terminal)
cd ../frontend
npm install
npm run dev
```

Visit http://localhost:3000 and login with:
- **Email**: user@example.com  
- **Password**: password123

The database initializes automatically on first run!

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

### 🎭 **Intelligent Question Diversity**
- **Semantic analysis** prevents repetitive themes (no more "Transformer obsession")
- **Context-aware generation** includes recent question history in AI prompts
- **Cross-session tracking** maintains diversity across learning sessions
- **Automatic retry** regenerates questions that are too similar
- **Concept cooldowns** ensure varied learning experiences

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
│   ├── question_diversity_service.py    # Semantic question diversity
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

### 🎯 **Intelligent Question Diversity**
The system generates sophisticated, varied questions that explore different aspects of topics, preventing repetitive themes. Rather than asking basic repetitive questions, the AI creates complex inquiries about advanced topics like fine-tuning Transformer models with CNNs for image-based text processing.

### 🌟 **Key Question Diversity Features:**
- **Semantic Analysis**: Prevents asking similar questions about the same concepts
- **Context Awareness**: Includes recent question history in AI generation prompts  
- **Automatic Retry**: Regenerates questions that are too similar to recent ones
- **Cross-Session Tracking**: Maintains diversity across learning sessions
- **Concept Cooldowns**: Avoids overused themes like "Transformer architecture obsession"

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

### 🎯 Question Diversity System
Prevents repetitive themes using advanced semantic analysis:

```python
# Concept extraction and diversity checking
recent_concepts = await get_recent_question_history(user_id, topic_id, limit=5)
diversity_context = generate_diversity_prompt_context(recent_concepts)

# Enhanced AI prompt with diversity instructions
prompt = f"""Create a question about {topic}.
DIVERSITY CONTEXT: {diversity_context}
AVOID these recently covered themes: {overused_concepts}
CONSIDER exploring: {underexplored_concepts}"""

# Validate generated question
proposed_concepts = extract_question_concepts(generated_question)
diversity_score = check_concept_diversity(proposed_concepts, recent_concepts)

# Retry if too similar (diversity_score < 0.3)
if not diverse_enough:
    regenerate_with_stronger_diversity_instructions()
```

**Key Components:**
- `QuestionDiversityService` - Semantic analysis and concept tracking
- `TopicQuestionHistory` - Cross-session question and concept storage  
- Enhanced prompts with "AVOID these themes" instructions
- Automatic retry for questions scoring below diversity threshold
- Real-time concept extraction using pattern matching and NLP

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