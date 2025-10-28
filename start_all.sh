#!/bin/bash

# Stop all existing processes first
echo "🛑 Stopping existing processes..."
pkill -9 -f "react-scripts" 2>/dev/null || true
pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true
pkill -9 -f "node.*start" 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start both Backend and Frontend

echo "🚀 Starting Runway Finance Application..."
echo ""

# Make scripts executable
chmod +x start_backend.sh
chmod +x start_frontend.sh

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    pkill -f "uvicorn api.main:app" 2>/dev/null
    pkill -f "react-scripts start" 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "📡 Starting Backend API..."
./start_backend.sh > backend.log 2>&1 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 5

# Start frontend
echo "🎨 Starting Frontend..."
./start_frontend.sh

# If we reach here, cleanup
cleanup

