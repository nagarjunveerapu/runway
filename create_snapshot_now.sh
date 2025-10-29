#!/bin/bash

echo "📸 Creating Net Worth Snapshot..."
echo ""

# Get JWT token (you'll need to replace with actual token from browser)
# Check browser localStorage or cookies for the JWT token
TOKEN="YOUR_JWT_TOKEN_HERE"

if [ "$TOKEN" = "YOUR_JWT_TOKEN_HERE" ]; then
  echo "⚠️  Please get your JWT token from the browser:"
  echo ""
  echo "1. Open browser DevTools (F12)"
  echo "2. Go to Application > Local Storage"
  echo "3. Copy the 'token' value"
  echo "4. Edit this script and replace YOUR_JWT_TOKEN_HERE"
  echo ""
  echo "Or run this command with your token:"
  echo "curl -X POST http://localhost:8000/api/v1/net-worth/snapshot -H 'Authorization: Bearer YOUR_TOKEN'"
  exit 1
fi

# Create snapshot
curl -X POST http://localhost:8000/api/v1/net-worth/snapshot \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

echo ""
echo "✅ Snapshot created!"
echo ""
echo "Refresh your browser to see the updated timeline."

