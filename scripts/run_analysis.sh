#!/bin/bash
echo "🛡️ Starting ModelGuard..."

if [ ! -d "venv" ]; then
    echo "Creating Virtual Environment..."
    python -m venv venv
fi

echo "Checking Data..."
if [ ! -f "data/housing_current.csv" ]; then
    python scripts/download_data.py
fi

echo "Launching Server..."
uvicorn app.main:app --reload