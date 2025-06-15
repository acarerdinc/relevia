#!/usr/bin/env bash
# Render build script

echo "Starting Render build..."

# Install dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed!"