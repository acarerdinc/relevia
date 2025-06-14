-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create topics table
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    difficulty_min INTEGER DEFAULT 1,
    difficulty_max INTEGER DEFAULT 10
);

-- Create questions table
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    difficulty INTEGER NOT NULL,
    options JSON,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    mastery_level VARCHAR(50) DEFAULT 'novice',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create topic_prerequisites table
CREATE TABLE IF NOT EXISTS topic_prerequisites (
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    prerequisite_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (topic_id, prerequisite_id)
);

-- Create quiz_sessions table
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    session_type VARCHAR(50) DEFAULT 'topic_focused',
    mastery_level VARCHAR(50) DEFAULT 'novice'
);

-- Create quiz_questions table
CREATE TABLE IF NOT EXISTS quiz_questions (
    id SERIAL PRIMARY KEY,
    quiz_session_id INTEGER NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_answer TEXT,
    is_correct BOOLEAN,
    answered_at TIMESTAMP,
    time_spent INTEGER,
    user_action VARCHAR(50),
    interest_signal FLOAT DEFAULT 0.0
);

-- Create user_skill_progress table
CREATE TABLE IF NOT EXISTS user_skill_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    skill_level FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 0.5,
    questions_answered INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    mastery_level VARCHAR(50) DEFAULT 'novice',
    current_mastery_level VARCHAR(50) DEFAULT 'novice',
    mastery_questions_answered JSON DEFAULT '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
    is_unlocked BOOLEAN DEFAULT TRUE,
    unlocked_at TIMESTAMP,
    proficiency_threshold_met BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_interests table
CREATE TABLE IF NOT EXISTS user_interests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    interest_score FLOAT DEFAULT 0.5,
    interaction_count INTEGER DEFAULT 0,
    time_spent INTEGER DEFAULT 0,
    preference_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create dynamic_topic_unlocks table
CREATE TABLE IF NOT EXISTS dynamic_topic_unlocks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    unlocked_topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    unlock_trigger VARCHAR(50),
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create learning_goals table
CREATE TABLE IF NOT EXISTS learning_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_type VARCHAR(50),
    target_topics JSON,
    target_proficiency VARCHAR(50),
    deadline TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    progress FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create topic_question_history table
CREATE TABLE IF NOT EXISTS topic_question_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    session_id INTEGER NOT NULL REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    question_content TEXT NOT NULL,
    extracted_concepts JSON,
    asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test users with bcrypt hashed passwords
-- Password: fenapass1
-- Password: ordekzeze1  
-- Password: zazapass1

INSERT INTO users (email, username, hashed_password, is_active) VALUES
('info@acarerdinc.com', 'acarerdinc', '$2b$12$MpsuBqqnS68EusawjQpNR.XfsBU10ZxMGYJOY2OZH8Q9CCRx2aaLu', true),
('ogulcancelik@gmail.com', 'ogulcancelik', '$2b$12$HJ.Cr5.6e.Hdu/fthvsHNeFzA7Hd4AH3Y0ahmTYiho.TjKTIt5Pie', true),
('begumcitamak@gmail.com', 'begumcitamak', '$2b$12$KICM8SZptoM.1o3qygwneO1OXpOUho7KixeB6mQcp4tZfv1aVzYjO', true)
ON CONFLICT (email) DO NOTHING;