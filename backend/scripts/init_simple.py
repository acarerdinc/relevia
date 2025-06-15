#!/usr/bin/env python3
"""
Initialize database with minimal data using raw SQL
"""
import sqlite3
from datetime import datetime

def init_database():
    conn = sqlite3.connect('relevia.db')
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE id = 1")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            print("Creating default user...")
            # Hash for 'password123' 
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiLXCJIwaJem'
            cursor.execute("""
                INSERT INTO users (id, email, username, hashed_password, is_active)
                VALUES (1, 'user@example.com', 'testuser', ?, 1)
            """, (password_hash,))
            print("✅ Created user: user@example.com / password123")
        else:
            print("✅ User already exists")
        
        # Check if topics exist
        cursor.execute("SELECT COUNT(*) FROM topics")
        topic_count = cursor.fetchone()[0]
        
        if topic_count == 0:
            print("Creating root AI topic...")
            cursor.execute("""
                INSERT INTO topics (name, description, parent_id, difficulty_min, difficulty_max)
                VALUES ('Artificial Intelligence', 
                        'The study and development of computer systems able to perform tasks that typically require human intelligence',
                        NULL, 1, 10)
            """)
            topic_id = cursor.lastrowid
            print(f"✅ Created root topic (ID: {topic_id})")
            
            # Create skill progress record (without skill_level and confidence)
            cursor.execute("""
                INSERT INTO user_skill_progress 
                (user_id, topic_id, questions_answered, correct_answers, 
                 mastery_level, current_mastery_level, mastery_questions_answered,
                 is_unlocked, unlocked_at, proficiency_threshold_met)
                VALUES (1, ?, 0, 0, 'novice', 'novice', 
                        '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
                        1, ?, 0)
            """, (topic_id, datetime.now().isoformat()))
            print("✅ Unlocked root topic for user")
            
            # Create unlock record
            cursor.execute("""
                INSERT INTO dynamic_topic_unlocks 
                (user_id, parent_topic_id, unlocked_topic_id, unlock_trigger, unlocked_at)
                VALUES (1, NULL, ?, 'root_topic', ?)
            """, (topic_id, datetime.now().isoformat()))
            print("✅ Created unlock record")
        else:
            print(f"✅ Topics already exist ({topic_count} topics)")
            
            # Make sure user has access to root topic
            cursor.execute("""
                SELECT COUNT(*) FROM user_skill_progress 
                WHERE user_id = 1 AND topic_id IN (
                    SELECT id FROM topics WHERE parent_id IS NULL
                )
            """)
            has_access = cursor.fetchone()[0]
            
            if has_access == 0:
                cursor.execute("SELECT id FROM topics WHERE parent_id IS NULL LIMIT 1")
                root_topic = cursor.fetchone()
                if root_topic:
                    root_id = root_topic[0]
                    cursor.execute("""
                        INSERT INTO user_skill_progress 
                        (user_id, topic_id, questions_answered, correct_answers, 
                         mastery_level, current_mastery_level, mastery_questions_answered,
                         is_unlocked, unlocked_at, proficiency_threshold_met)
                        VALUES (1, ?, 0, 0, 'novice', 'novice', 
                                '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
                                1, ?, 0)
                    """, (root_id, datetime.now().isoformat()))
                    print(f"✅ Granted access to root topic (ID: {root_id})")
        
        conn.commit()
        print("\n✅ Database initialized successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM topics")
        topic_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user_skill_progress WHERE user_id = 1")
        progress_count = cursor.fetchone()[0]
        
        print(f"\n📊 Summary:")
        print(f"   - Topics: {topic_count}")
        print(f"   - User progress records: {progress_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()