"""
Migrate database to remove skill_level and confidence columns
Safe migration that handles SQLite limitations
"""
import sqlite3
import shutil
from datetime import datetime

def migrate_database():
    # Backup the database first
    backup_name = f"relevia_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2('relevia.db', backup_name)
    print(f"Created backup: {backup_name}")
    
    conn = sqlite3.connect('relevia.db')
    cursor = conn.cursor()
    
    try:
        # SQLite doesn't support dropping columns directly, so we need to recreate the table
        print("Migrating user_skill_progress table...")
        
        # Create new table without skill_level and confidence
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_skill_progress_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                questions_answered INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                mastery_level TEXT DEFAULT 'novice',
                current_mastery_level TEXT DEFAULT 'novice',
                mastery_questions_answered TEXT DEFAULT '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}',
                is_unlocked BOOLEAN DEFAULT 1,
                unlocked_at TIMESTAMP,
                proficiency_threshold_met BOOLEAN DEFAULT 0,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (topic_id) REFERENCES topics (id)
            )
        """)
        
        # Copy data from old table to new table (excluding skill_level and confidence)
        cursor.execute("""
            INSERT INTO user_skill_progress_new 
            (id, user_id, topic_id, questions_answered, correct_answers, 
             mastery_level, current_mastery_level, mastery_questions_answered,
             is_unlocked, unlocked_at, proficiency_threshold_met, last_seen)
            SELECT 
                id, user_id, topic_id, questions_answered, correct_answers,
                mastery_level, current_mastery_level, mastery_questions_answered,
                is_unlocked, unlocked_at, proficiency_threshold_met, last_seen
            FROM user_skill_progress
        """)
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE user_skill_progress")
        cursor.execute("ALTER TABLE user_skill_progress_new RENAME TO user_skill_progress")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_user_id ON user_skill_progress (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_topic_id ON user_skill_progress (topic_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_user_skill_progress_id ON user_skill_progress (id)")
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the new schema
        cursor.execute("PRAGMA table_info(user_skill_progress)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"New columns: {columns}")
        
        # Check that skill_level and confidence are gone
        if 'skill_level' not in columns and 'confidence' not in columns:
            print("✅ skill_level and confidence columns successfully removed")
        else:
            print("❌ Migration may have failed - old columns still present")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()