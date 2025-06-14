"""
Centralized logging configuration for Relevia backend
- Structured logging with rotation and cleanup
- Performance tracking for debugging
- Automatic log file management
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import asyncio
from typing import Optional

# Create logs directory if it doesn't exist (skip on Vercel)
if not os.environ.get('VERCEL'):
    LOGS_DIR = Path(__file__).parent.parent / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
else:
    LOGS_DIR = None

class PerformanceLogger:
    """Logger specifically for tracking performance metrics"""
    
    def __init__(self):
        self.timers = {}
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{int(time.time() * 1000)}"
        self.timers[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str, context: str = "") -> float:
        """End timing and log the duration"""
        if timer_id not in self.timers:
            return 0.0
        
        duration_ms = (time.time() - self.timers[timer_id]) * 1000
        del self.timers[timer_id]
        
        # Log performance
        perf_logger = logging.getLogger('performance')
        perf_logger.info(f"{timer_id.split('_')[0]}: {duration_ms:.1f}ms {context}")
        
        return duration_ms

def setup_console_logging():
    """Setup console-only logging for Vercel"""
    logger = logging.getLogger('relevia')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.propagate = False
    
    return logger

def setup_logging():
    """Setup logging configuration"""
    # Check if running on Vercel
    if os.environ.get('VERCEL'):
        return setup_console_logging()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # 1. Main application logger
    main_logger = logging.getLogger('relevia')
    main_logger.setLevel(logging.DEBUG)
    
    # Rotating file handler for main logs (10MB max, keep 5 files)
    main_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'relevia.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(detailed_formatter)
    main_handler.setLevel(logging.DEBUG)
    main_logger.addHandler(main_handler)
    
    # 2. Performance logger (separate file)
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.INFO)
    
    perf_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'performance.log',
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    perf_handler.setFormatter(simple_formatter)
    perf_logger.addHandler(perf_handler)
    
    # 3. API request logger
    api_logger = logging.getLogger('api')
    api_logger.setLevel(logging.INFO)
    
    api_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'api.log',
        maxBytes=5*1024*1024,   # 5MB
        backupCount=3
    )
    api_handler.setFormatter(detailed_formatter)
    api_logger.addHandler(api_handler)
    
    # 4. Gemini API logger (for debugging slow responses)
    gemini_logger = logging.getLogger('gemini')
    gemini_logger.setLevel(logging.DEBUG)
    
    gemini_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'gemini.log',
        maxBytes=2*1024*1024,   # 2MB
        backupCount=2
    )
    gemini_handler.setFormatter(detailed_formatter)
    gemini_logger.addHandler(gemini_handler)
    
    # 5. Error logger (separate for easy monitoring)
    error_logger = logging.getLogger('errors')
    error_logger.setLevel(logging.ERROR)
    
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'errors.log',
        maxBytes=5*1024*1024,   # 5MB
        backupCount=5
    )
    error_handler.setFormatter(detailed_formatter)
    error_logger.addHandler(error_handler)
    
    # Console handler for development (optional)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Add console to main logger only
    main_logger.addHandler(console_handler)
    
    # Prevent duplicate logs
    main_logger.propagate = False
    perf_logger.propagate = False
    api_logger.propagate = False
    gemini_logger.propagate = False
    error_logger.propagate = False
    
    return main_logger

def cleanup_old_logs(days_to_keep: int = 7):
    """Remove log files older than specified days"""
    if not LOGS_DIR:
        return  # Skip on Vercel
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    cleaned_count = 0
    for log_file in LOGS_DIR.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_date.timestamp():
            try:
                log_file.unlink()
                cleaned_count += 1
            except OSError:
                pass  # File might be in use
    
    if cleaned_count > 0:
        logger = logging.getLogger('relevia')
        logger.info(f"Cleaned up {cleaned_count} old log files")

# Global performance logger instance
performance_logger = PerformanceLogger()

# Auto-setup logging when module is imported
logger = setup_logging()

# Schedule log cleanup (run once when module loads)
try:
    cleanup_old_logs()
except Exception:
    pass  # Don't fail if cleanup fails