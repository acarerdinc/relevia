from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    quiz_sessions = relationship("QuizSession", back_populates="user")
    skill_progress = relationship("UserSkillProgress", back_populates="user")

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    difficulty_min = Column(Integer, default=1)
    difficulty_max = Column(Integer, default=10)
    
    # Relationships
    parent = relationship("Topic", remote_side=[id])
    children = relationship("Topic")
    prerequisites = relationship(
        "Topic",
        secondary="topic_prerequisites",
        primaryjoin="Topic.id==topic_prerequisites.c.topic_id",
        secondaryjoin="Topic.id==topic_prerequisites.c.prerequisite_id",
    )
    questions = relationship("Question", back_populates="topic")

class TopicPrerequisite(Base):
    __tablename__ = "topic_prerequisites"
    
    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True)
    prerequisite_id = Column(Integer, ForeignKey("topics.id"), primary_key=True)

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    content = Column(Text, nullable=False)
    question_type = Column(String, nullable=False)  # multiple_choice, true_false, short_answer
    options = Column(JSON)  # For multiple choice
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)
    difficulty = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    topic = relationship("Topic", back_populates="questions")
    quiz_questions = relationship("QuizQuestion", back_populates="question")

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)  # Nullable for adaptive sessions
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    session_type = Column(String, default="topic_focused")  # "topic_focused" or "adaptive"
    
    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    quiz_questions = relationship("QuizQuestion", back_populates="quiz_session")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    quiz_session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(Text)
    is_correct = Column(Boolean)
    answered_at = Column(DateTime(timezone=True))
    time_spent = Column(Integer)  # seconds
    user_action = Column(String)  # answer, teach_me, skip
    interest_signal = Column(Float, default=0.0)  # Numeric interest signal
    
    # Relationships
    quiz_session = relationship("QuizSession", back_populates="quiz_questions")
    question = relationship("Question", back_populates="quiz_questions")

class UserSkillProgress(Base):
    __tablename__ = "user_skill_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    skill_level = Column(Float, default=0.5)  # 0-1 probability
    confidence = Column(Float, default=0.5)  # 0-1
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    mastery_level = Column(String, default="novice")  # novice, beginner, intermediate, advanced, expert
    is_unlocked = Column(Boolean, default=True)  # Whether user can access this topic
    unlocked_at = Column(DateTime(timezone=True))
    proficiency_threshold_met = Column(Boolean, default=False)  # For unlocking subtopics
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="skill_progress")

class UserInterest(Base):
    __tablename__ = "user_interests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    interest_score = Column(Float, default=0.5)  # 0-1, how interested user is
    interaction_count = Column(Integer, default=0)  # Number of times engaged with topic
    time_spent = Column(Integer, default=0)  # Total time spent in seconds
    preference_type = Column(String)  # explicit, implicit, inferred
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    topic = relationship("Topic")

class DynamicTopicUnlock(Base):
    __tablename__ = "dynamic_topic_unlocks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    unlocked_topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    unlock_trigger = Column(String)  # proficiency, interest, exploration
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    parent_topic = relationship("Topic", foreign_keys=[parent_topic_id])
    unlocked_topic = relationship("Topic", foreign_keys=[unlocked_topic_id])

class LearningGoal(Base):
    __tablename__ = "learning_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String)  # skill_mastery, exploration, certification
    target_topics = Column(JSON)  # List of topic IDs
    target_proficiency = Column(String)  # beginner, intermediate, advanced, expert
    deadline = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    progress = Column(Float, default=0.0)  # 0-1
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")

class TopicQuestionHistory(Base):
    __tablename__ = "topic_question_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False)
    question_content = Column(Text, nullable=False)  # Store question text for analysis
    extracted_concepts = Column(JSON)  # Key concepts/themes from the question
    asked_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    topic = relationship("Topic")
    question = relationship("Question")
    session = relationship("QuizSession")