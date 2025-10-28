#!/bin/bash

# Cleanup all Runway Finance processes

echo "🧹 Cleaning up all processes..."

# Kill React/Node processes
echo "Stopping React frontend..."
pkill -f "react-scripts" || true
pkill -f "node.*start" || true

# Kill Python/uvicorn processes
echo "Stopping Backend API..."
pkill -f "uvicorn api.main:app" || true
pkill -f "python.*main.py" || true

# Kill processes on specific ports
echo "Clearing ports 3000, 3001, 8000..."
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

sleep 2

echo "✅ Cleanup complete!"
echo ""
echo "Verify no processes are running:"
echo "  - Backend on 8000: lsof -ti:8000"
echo "  - Frontend on 3000: lsof -ti:3000"
echo "  - Frontend on 3001: lsof -ti:3001"
echo ""



