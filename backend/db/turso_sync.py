"""Synchronous Turso database operations for use with sync_to_async"""
import libsql_client
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os

class TursoSyncDB:
    """Synchronous database operations for Turso"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        # Create a sync engine for Turso
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def execute_query(self, query: str, params: dict = None):
        """Execute a query and return results"""
        with self.SessionLocal() as session:
            result = session.execute(text(query), params or {})
            if query.strip().upper().startswith('SELECT'):
                return result.fetchall()
            else:
                session.commit()
                return result
    
    def get_user_by_email(self, email: str):
        """Get user by email"""
        query = """
        SELECT id, email, username, hashed_password, is_active, created_at 
        FROM users 
        WHERE email = :email
        """
        with self.SessionLocal() as session:
            result = session.execute(text(query), {"email": email})
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "email": row[1],
                    "username": row[2],
                    "hashed_password": row[3],
                    "is_active": row[4],
                    "created_at": row[5]
                }
            return None
    
    def test_connection(self):
        """Test database connection"""
        with self.SessionLocal() as session:
            result = session.execute(text("SELECT 1"))
            return result.scalar() == 1

# Global instance
_turso_db = None

def get_turso_db(database_url: str) -> TursoSyncDB:
    """Get or create Turso database instance"""
    global _turso_db
    if _turso_db is None:
        _turso_db = TursoSyncDB(database_url)
    return _turso_db