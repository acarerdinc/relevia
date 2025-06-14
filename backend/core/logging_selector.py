"""
Select appropriate logging configuration based on environment
"""
import os

# Check if running on Vercel
if os.environ.get('VERCEL'):
    from core.logging_config_vercel import *
else:
    from core.logging_config import *