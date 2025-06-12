#!/bin/bash
# Quick reset script for testing
source venv/bin/activate
PYTHONPATH=/Users/acar/projects/relevia/backend python scripts/setup/reset_and_reseed.py
echo "🎯 Ready for fresh infinite learning session!"
echo "📱 Please refresh your browser to see the changes!"