"""
SQLite timezone fix for SQLAlchemy
Makes sure all datetime values are timezone-aware
"""
from sqlalchemy import DateTime, TypeDecorator
from datetime import datetime, timezone
import dateutil.parser

class TZDateTime(TypeDecorator):
    """A DateTime type that ensures timezone-aware datetimes"""
    impl = DateTime
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            if not hasattr(value, 'tzinfo') or value.tzinfo is None:
                # Make timezone-aware if it isn't already
                value = value.replace(tzinfo=timezone.utc)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            if not hasattr(value, 'tzinfo') or value.tzinfo is None:
                # For SQLite, try to parse the string representation
                if hasattr(value, 'isoformat'):
                    # It's already a datetime object, just add timezone
                    value = value.replace(tzinfo=timezone.utc)
                else:
                    # It's a string, parse it
                    try:
                        value = dateutil.parser.parse(str(value))
                        if value.tzinfo is None:
                            value = value.replace(tzinfo=timezone.utc)
                    except:
                        # Fallback to assuming UTC
                        value = datetime.fromisoformat(str(value).replace(' ', 'T')).replace(tzinfo=timezone.utc)
        return value