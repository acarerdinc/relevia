import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Force the use of asyncio from the venv
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Use synchronous SQLAlchemy for simplicity
DATABASE_URL = "postgresql://user:pass@localhost/relevia"

# Try to connect with the actual database
try:
    # Check if .env file exists and load it
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.getenv('DATABASE_URL', DATABASE_URL)
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        print("=== CHECKING MACHINE LEARNING VISIBILITY ===\n")
        
        # Get Machine Learning topic
        ml_topic = session.execute(
            text("SELECT id, name, parent_id FROM topics WHERE name = 'Machine Learning'")
        ).fetchone()
        
        if ml_topic:
            print(f"✅ Machine Learning found: ID={ml_topic[0]}, Parent={ml_topic[2]}")
            
            # Get its children
            children = session.execute(
                text("SELECT id, name, difficulty_min, difficulty_max FROM topics WHERE parent_id = :parent_id ORDER BY name"),
                {"parent_id": ml_topic[0]}
            ).fetchall()
            
            print(f"\n📊 Machine Learning has {len(children)} children in topics table:")
            for child in children:
                print(f"   - {child[1]} (ID={child[0]}, Difficulty={child[2]}-{child[3]})")
            
            # Check UserSkillProgress for these children
            print(f"\n🔍 Checking UserSkillProgress for user_id=1:")
            for child in children:
                progress = session.execute(
                    text("""
                        SELECT is_unlocked, current_mastery_level, questions_answered 
                        FROM user_skill_progress 
                        WHERE topic_id = :topic_id AND user_id = 1
                    """),
                    {"topic_id": child[0]}
                ).fetchone()
                
                if progress:
                    print(f"   ✅ {child[1]}: is_unlocked={progress[0]}, mastery={progress[1]}, questions={progress[2]}")
                else:
                    print(f"   ❌ {child[1]}: NO UserSkillProgress record (won't show in tree!)")
            
            # Check ML's own progress
            print(f"\n📈 Machine Learning's own progress:")
            ml_progress = session.execute(
                text("""
                    SELECT current_mastery_level, questions_answered, is_unlocked, proficiency_threshold_met 
                    FROM user_skill_progress 
                    WHERE topic_id = :topic_id AND user_id = 1
                """),
                {"topic_id": ml_topic[0]}
            ).fetchone()
            
            if ml_progress:
                print(f"   Mastery: {ml_progress[0]}, Questions: {ml_progress[1]}, Unlocked: {ml_progress[2]}")
                print(f"   Proficiency Met: {ml_progress[3]}")
            else:
                print("   ❌ No progress record found")
                
        else:
            print("❌ Machine Learning topic not found!")
            
except Exception as e:
    print(f"Database connection failed: {e}")
    print("\nTrying with SQLite relevia.db instead...")
    
    # Fallback to SQLite
    import sqlite3
    
    try:
        conn = sqlite3.connect('relevia.db')
        cursor = conn.cursor()
        
        # Get ML topic
        cursor.execute("SELECT id, name FROM topics WHERE name = 'Machine Learning'")
        ml_topic = cursor.fetchone()
        
        if ml_topic:
            print(f"\n✅ Machine Learning found in SQLite: ID={ml_topic[0]}")
            
            # Get children
            cursor.execute("SELECT id, name FROM topics WHERE parent_id = ?", (ml_topic[0],))
            children = cursor.fetchall()
            
            print(f"Children found: {len(children)}")
            for child in children:
                print(f"   - {child[1]} (ID={child[0]})")
        
        conn.close()
    except Exception as e2:
        print(f"SQLite also failed: {e2}")