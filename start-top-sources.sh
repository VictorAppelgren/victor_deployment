#!/bin/bash
# Start script for Top Sources Worker
# Runs main_top_sources.py (premium source ingestion)

set -e

echo "============================================"
echo "🚀 SAGA TOP SOURCES WORKER STARTING"
echo "============================================"
echo "✅ Dependencies pre-installed in Docker image"
echo ""

cd /app/saga-graph

# Run top sources worker
echo "🚀 Starting Top Sources Worker (main_top_sources.py)..."
python main_top_sources.py

echo ""
echo "============================================"
echo "⚠️  TOP SOURCES WORKER STOPPED"
echo "============================================"
