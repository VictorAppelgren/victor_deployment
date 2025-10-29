#!/bin/bash
# Start script for APIs container
# Runs Backend API + Graph API

set -e

echo "============================================"
echo "🚀 SAGA APIS CONTAINER STARTING"
echo "============================================"
echo "✅ Dependencies pre-installed in Docker image"
echo ""

echo "🚀 Starting Backend API on port 8000..."
cd /app/saga-be
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "🚀 Starting Graph API on port 8001..."
cd /app/graph-functions
python API/graph_api.py &
GRAPH_PID=$!

echo ""
echo "============================================"
echo "✅ ALL APIS STARTED"
echo "   - Backend API: http://0.0.0.0:8000"
echo "   - Graph API:   http://0.0.0.0:8001"
echo "============================================"
echo ""

# Wait for both processes
wait $BACKEND_PID $GRAPH_PID
