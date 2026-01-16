#!/bin/bash
# Start script for Writer Worker
# Runs write_all.py --loop (24/7 analysis writing)

set -e

echo "============================================"
echo "SAGA WRITER WORKER STARTING"
echo "============================================"
echo "Dependencies pre-installed in Docker image"
echo ""

cd /app/graph-functions

# Run writer in continuous loop mode
echo "Starting Write All Pipeline (continuous)..."
python entrypoints/write_all.py --loop

echo ""
echo "============================================"
echo "WRITER WORKER STOPPED"
echo "============================================"
