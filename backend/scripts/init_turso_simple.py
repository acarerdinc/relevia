"""
Simple Turso database initialization using libsql directly
"""
import libsql_experimental as libsql
import os
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Get Turso credentials
turso_url = os.environ.get("TURSO_DATABASE_URL", "libsql://relevia-acarerdinc.aws-eu-west-1.turso.io")
turso_token = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NDk5MjE4NTksImlkIjoiYWQzNWJmZTctMjg5MS00YjVkLWJkOGYtMTMwYjRkMDZlOTk3IiwicmlkIjoiMGRhMWY4YzQtNWNhOC00MjQwLWEwZjktZmViMzkwY2Y1Mzc3In0.ksteejk5iFqb2fgm3Z-WrT-05nFDvl6IiyBdzMlgBKO6jTDziwg_mUJd9aFPwWPVxzC88J51CoIOZhHevNjKBg")

print(f"🔗 Connecting to Turso database...")

# Connect to Turso
conn = libsql.connect(turso_url, auth_token=turso_token)
cursor = conn.cursor()

# Create tables
print("📋 Creating tables...")

# Users table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Topics table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        parent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_id) REFERENCES topics(id)
    )
""")

# Other tables
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        mastery_level REAL DEFAULT 0.0,
        last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id),
        UNIQUE(user_id, topic_id)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        score REAL NOT NULL,
        total_questions INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    )
""")

conn.commit()
print("✅ Tables created successfully!")

# Check if users exist
cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]

if user_count > 0:
    print(f"ℹ️  {user_count} users already exist in database. Skipping user creation.")
else:
    print("👥 Creating test users...")
    
    # Test users
    test_users = [
        ("acarerdinc", "info@acarerdinc.com", pwd_context.hash("fenapass1")),
        ("ogulcan", "ogulcancelik@gmail.com", pwd_context.hash("ordekzeze1")),
        ("begum", "begumcitamak@gmail.com", pwd_context.hash("zazapass1"))
    ]
    
    for username, email, hashed_password in test_users:
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        print(f"✅ Created user: {email}")
    
    conn.commit()

# Add root topic if needed
cursor.execute("SELECT COUNT(*) FROM topics WHERE name = 'Technology'")
topic_exists = cursor.fetchone()[0] > 0

if not topic_exists:
    print("📚 Creating root topic...")
    cursor.execute(
        "INSERT INTO topics (name, description) VALUES (?, ?)",
        ("Technology", "Root topic for technology learning")
    )
    conn.commit()
    print("✅ Created root topic: Technology")
else:
    print("ℹ️  Root topic already exists.")

# Show summary
cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM topics")
topic_count = cursor.fetchone()[0]

print(f"\n📊 Database Summary:")
print(f"   - Users: {user_count}")
print(f"   - Topics: {topic_count}")

conn.close()
print("\n🎉 Database initialization complete!")