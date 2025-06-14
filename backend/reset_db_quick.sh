#!/bin/bash
# Quick Database Reset Script (No Confirmation)
# ⚠️  WARNING: This will immediately delete all data!

echo "🔄 Quick database reset in progress..."

# Find python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found"
    exit 1
fi

$PYTHON_CMD reset_database.py --force