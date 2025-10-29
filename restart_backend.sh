#!/bin/bash

echo "🔄 Restarting backend server..."
echo ""

# Kill existing backend process
echo "Stopping existing backend..."
pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

sleep 2

echo "Starting backend..."
cd runway-app-backend

# Start backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &

echo ""
echo "✅ Backend restarted on port 8000"
echo "📝 Logs: tail -f runway-app-backend/backend.log"
echo ""
echo "Refresh your browser to see updated timeline!"

