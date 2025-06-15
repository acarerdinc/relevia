#!/usr/bin/env python3
"""
Simple initialization to get the system running
"""
import sqlite3

def init_db():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE id = 1")
        user_exists = cursor.fetchone()[0] > 0
        
        if not user_exists:
            print("Creating default user...")
            # Hash for 'password123' using bcrypt
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiLXCJIwaJem'
            cursor.execute("""
                INSERT INTO users (id, email, username, hashed_password, is_active)
                VALUES (1, 'user@example.com', 'testuser', ?, 1)
            """, (password_hash,))
            print("✅ Created user: user@example.com / password123")
        
        # Create root AI topic
        cursor.execute("SELECT COUNT(*) FROM topics WHERE parent_id IS NULL")
        has_root = cursor.fetchone()[0] > 0
        
        if not has_root:
            print("Creating root AI topic...")
            cursor.execute("""
                INSERT INTO topics (name, description, parent_id, difficulty_min, difficulty_max)
                VALUES ('Artificial Intelligence', 
                        'The study and development of computer systems able to perform tasks that typically require human intelligence',
                        NULL, 1, 10)
            """)
            topic_id = cursor.lastrowid
            print(f"✅ Created root topic with ID: {topic_id}")
            
            # Create skill progress (without skill_level and confidence)
            cursor.execute("""
                INSERT INTO user_skill_progress 
                (user_id, topic_id, questions_answered, correct_answers, 
                 mastery_level, current_mastery_level, mastery_questions_answered,
                 is_unlocked, unlocked_at, proficiency_threshold_met)
                VALUES (1, ?, 0, 0, 'novice', 'novice', 
                        '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
                        1, datetime('now'), 0)
            """, (topic_id,))
            print("✅ Unlocked root topic for user")
            
            # Create unlock record
            cursor.execute("""
                INSERT INTO dynamic_topic_unlocks 
                (user_id, parent_topic_id, unlocked_topic_id, unlock_trigger, unlocked_at)
                VALUES (1, NULL, ?, 'root_topic', datetime('now'))
            """, (topic_id,))
            print("✅ Created unlock record")
        
        conn.commit()
        print("\n✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()