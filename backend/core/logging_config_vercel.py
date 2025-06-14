"""
Simplified logging configuration for Vercel deployment
Uses console output only (no file handlers)
"""
import logging
import sys

def setup_logging():
    """Setup console-only logging for Vercel"""
    # Create main logger
    logger = logging.getLogger('relevia')
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Simple formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

# Initialize logger
logger = setup_logging()

# Create child loggers (no file handlers)
api_logger = logger.getChild('api')
quiz_logger = logger.getChild('quiz')
gemini_logger = logger.getChild('gemini')
performance_logger = logger.getChild('performance')
error_logger = logger.getChild('error')