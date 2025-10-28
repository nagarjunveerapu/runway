#!/bin/bash

# Runway Finance API Startup Script

echo "🚀 Starting Runway Finance API..."
echo ""
echo "API Documentation will be available at:"
echo "  - Swagger UI: http://localhost:8000/docs"
echo "  - ReDoc:      http://localhost:8000/redoc"
echo "  - OpenAPI:    http://localhost:8000/openapi.json"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run FastAPI with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
