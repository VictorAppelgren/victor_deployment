#!/bin/bash
# Start script for Main Pipeline Worker
# Runs ingest_articles.py (24/7 topic processing pipeline)

set -e

echo "============================================"
echo "🚀 SAGA MAIN PIPELINE WORKER STARTING"
echo "============================================"
echo "✅ Dependencies pre-installed in Docker image"
echo ""

cd /app/graph-functions

# Run main pipeline (graph should be bootstrapped)
echo "🚀 Starting Ingest Articles Pipeline..."
python entrypoints/ingest_articles.py

echo ""
echo "============================================"
echo "⚠️  MAIN PIPELINE STOPPED"
echo "============================================"
