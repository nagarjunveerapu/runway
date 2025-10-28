#!/bin/bash

# Start Runway Finance Frontend
echo "🚀 Starting Runway Finance Frontend..."
echo ""
echo "Frontend will run at: http://localhost:3000"
echo ""

cd runway-app

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the React app
echo "✅ Starting React development server..."
npm start


