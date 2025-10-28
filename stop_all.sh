#!/bin/bash

echo "🛑 Stopping all Runway Finance processes..."

# Kill React/Node processes on port 3000
echo "Stopping processes on port 3000..."
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Kill React/Node processes on port 3001
echo "Stopping processes on port 3001..."
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

# Kill backend on port 8000
echo "Stopping backend on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Kill any React scripts
echo "Killing React processes..."
pkill -9 -f "react-scripts" 2>/dev/null || true

# Kill any uvicorn processes
echo "Killing Backend API processes..."
pkill -9 -f "uvicorn api.main:app" 2>/dev/null || true

# Kill any node processes related to start
pkill -9 -f "node.*start" 2>/dev/null || true

sleep 1

echo ""
echo "✅ All processes stopped!"
echo ""
echo "Verifying ports are free:"
lsof -i:3000 || echo "Port 3000 is free ✓"
lsof -i:3001 || echo "Port 3001 is free ✓"
lsof -i:8000 || echo "Port 8000 is free ✓"



