#!/bin/bash

# Saga Deployment Script
# Run this on your Digital Ocean server to deploy/rebuild

set -e  # Exit on any error

echo "🚀 SAGA DEPLOYMENT STARTING..."
echo "================================"

# Navigate to deployment directory
cd /opt/saga-graph/victor_deployment

echo ""
echo "📦 Step 1: Pulling latest code..."
# If you're using git, uncomment:
# git pull origin main

echo ""
echo "🛑 Step 2: Stopping existing containers..."
docker compose down

echo ""
echo "🔨 Step 3: Rebuilding images..."
docker compose build --no-cache

echo ""
echo "🚀 Step 4: Starting all services..."
docker compose up -d

echo ""
echo "⏳ Step 5: Waiting for services to be healthy..."
sleep 10

echo ""
echo "🔍 Step 6: Checking service status..."
docker compose ps

echo ""
echo "🏥 Step 7: Health check..."
echo "Backend API:"
curl -s http://localhost:8000/health | jq '.' || echo "❌ Backend not responding"

echo ""
echo "Graph API:"
curl -s http://localhost:8001/neo/health | jq '.' || echo "❌ Graph API not responding"

echo ""
echo "Frontend:"
curl -s http://localhost:5173 > /dev/null && echo "✅ Frontend responding" || echo "❌ Frontend not responding"

echo ""
echo "================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "🌐 Your app is available at:"
echo "   http://167.172.185.204/"
echo ""
echo "📊 View logs with:"
echo "   docker compose logs -f [service-name]"
echo ""
echo "🔍 Check status with:"
echo "   docker compose ps"
echo "================================"
