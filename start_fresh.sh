#!/bin/bash

# Fresh Start Script for Runway Finance

echo "🚀 Starting Runway Finance - Fresh Start"
echo ""

# Step 1: Cleanup
echo "Step 1/4: Cleaning up existing processes..."
pkill -f "react-scripts" 2>/dev/null || true
pkill -f "uvicorn api.main:app" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2
echo "✅ Cleaned up!"

# Step 2: Start Backend
echo ""
echo "Step 2/4: Starting Backend API..."
cd runway-app-backend

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Start backend in background
echo "Starting API server on port 8000..."
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "❌ Backend failed to start. Check backend.log for details."
    exit 1
fi

# Step 3: Start Frontend
echo ""
echo "Step 3/4: Starting Frontend..."
cd ../runway-app

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend
echo "Starting React on port 3000..."
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "Step 4/4: Services are starting..."
echo ""
echo "✅ Backend API: http://localhost:8000"
echo "✅ Frontend: http://localhost:3000"
echo "✅ API Docs: http://localhost:8000/docs"
echo ""
echo "Login with:"
echo "  Email: test@example.com"
echo "  Password: testpassword123"
echo ""
echo "Logs:"
echo "  Backend: tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait




