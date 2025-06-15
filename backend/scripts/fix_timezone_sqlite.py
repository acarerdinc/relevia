#!/usr/bin/env python3
"""
Fix timezone issues in SQLite database
SQLite doesn't handle timezones well, so we need to ensure consistency
"""
import sqlite3
from datetime import datetime, timezone

def fix_timezones():
    """Fix all datetime columns to ensure they're timezone-aware"""
    conn = sqlite3.connect('relevia.db')
    cursor = conn.cursor()
    
    try:
        # Get all quiz sessions
        cursor.execute("SELECT id, started_at FROM quiz_sessions")
        sessions = cursor.fetchall()
        
        print(f"Found {len(sessions)} quiz sessions to check")
        
        for session_id, started_at in sessions:
            if started_at and not started_at.endswith('+00:00') and not 'T' in started_at:
                # Convert to ISO format with timezone
                try:
                    # Parse the datetime
                    dt = datetime.fromisoformat(started_at.replace(' ', 'T'))
                    # Make it timezone aware
                    dt_aware = dt.replace(tzinfo=timezone.utc)
                    # Update in database
                    cursor.execute(
                        "UPDATE quiz_sessions SET started_at = ? WHERE id = ?",
                        (dt_aware.isoformat(), session_id)
                    )
                    print(f"Fixed session {session_id}: {started_at} -> {dt_aware.isoformat()}")
                except Exception as e:
                    print(f"Error fixing session {session_id}: {e}")
        
        # Fix user_skill_progress unlocked_at
        cursor.execute("SELECT id, unlocked_at FROM user_skill_progress WHERE unlocked_at IS NOT NULL")
        progress_records = cursor.fetchall()
        
        for progress_id, unlocked_at in progress_records:
            if unlocked_at and not unlocked_at.endswith('+00:00') and not 'T' in unlocked_at:
                try:
                    dt = datetime.fromisoformat(unlocked_at.replace(' ', 'T'))
                    dt_aware = dt.replace(tzinfo=timezone.utc)
                    cursor.execute(
                        "UPDATE user_skill_progress SET unlocked_at = ? WHERE id = ?",
                        (dt_aware.isoformat(), progress_id)
                    )
                    print(f"Fixed progress {progress_id}: {unlocked_at} -> {dt_aware.isoformat()}")
                except Exception as e:
                    print(f"Error fixing progress {progress_id}: {e}")
        
        conn.commit()
        print("✅ Timezone fixes applied")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_timezones()