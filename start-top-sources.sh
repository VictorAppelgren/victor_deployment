#!/bin/bash
# Start script for Top Sources Worker
# Runs ingest_top_sources.py (premium source ingestion)

set -e

echo "============================================"
echo "🚀 SAGA TOP SOURCES WORKER STARTING"
echo "============================================"
echo "✅ Dependencies pre-installed in Docker image"
echo ""

cd /app/graph-functions

# Run top sources worker
echo "🚀 Starting Ingest Top Sources Pipeline..."
python entrypoints/ingest_top_sources.py

echo ""
echo "============================================"
echo "⚠️  TOP SOURCES WORKER STOPPED"
echo "============================================"
