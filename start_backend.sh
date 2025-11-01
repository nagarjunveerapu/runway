#!/bin/bash

# Start Runway Finance Backend API
echo "🚀 Starting Runway Finance Backend API..."
echo ""
echo "Backend will run at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""

cd runway-app-backend

# Use DATABASE_URL from .env file if it exists, otherwise default to SQLite
# Don't override if .env file has DATABASE_URL set
if [ ! -f ".env" ] || ! grep -q "^DATABASE_URL=" .env; then
    # Only set SQLite if no DATABASE_URL in .env
    export DATABASE_URL="sqlite:///data/finance.db"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📥 Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Start the API server
echo "✅ Starting API server..."
python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000


