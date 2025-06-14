"""Initialize Vercel SQLite database with test users"""
import asyncio
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_vercel_database():
    """Initialize the Vercel SQLite database with test users"""
    # Use sync engine for initialization
    database_url = "sqlite:////tmp/relevia.db"
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Create users table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create topics table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                parent_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES topics(id)
            )
        """))
        
        # Check if users exist
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        
        if count == 0:
            # Insert test users
            users = [
                ("info@acarerdinc.com", "info", pwd_context.hash("fenapass1")),
                ("ogulcancelik@gmail.com", "ogulcan", pwd_context.hash("ordekzeze1")),
                ("begumcitamak@gmail.com", "begum", pwd_context.hash("zazapass1"))
            ]
            
            for email, username, hashed_password in users:
                conn.execute(text("""
                    INSERT INTO users (email, username, hashed_password, is_active)
                    VALUES (:email, :username, :hashed_password, 1)
                """), {"email": email, "username": username, "hashed_password": hashed_password})
            
            print(f"Created {len(users)} test users")
        
        # Insert AI topic if not exists
        result = conn.execute(text("SELECT COUNT(*) FROM topics WHERE name = 'Artificial Intelligence'"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO topics (name, description, parent_id, is_active)
                VALUES ('Artificial Intelligence', 'Study of intelligent agents and machines', NULL, 1)
            """))
            print("Created AI topic")
        
        conn.commit()
        print("Vercel database initialized successfully")

if __name__ == "__main__":
    asyncio.run(init_vercel_database())