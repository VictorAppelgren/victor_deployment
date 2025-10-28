#!/bin/bash
# Quick status check for all Saga services

echo "============================================"
echo "🔍 SAGA SERVICES STATUS"
echo "============================================"
echo ""

echo "📊 Docker Containers:"
docker-compose ps
echo ""

echo "============================================"
echo "🏥 Health Checks:"
echo "============================================"

echo -n "Backend API (8000): "
curl -s -f http://localhost:8000/health > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"

echo -n "Graph API (8001):   "
curl -s -f http://localhost:8001/neo/health > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"

echo -n "Neo4j (7474):       "
curl -s -f http://localhost:7474 > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"

echo -n "Frontend (5173):    "
curl -s -f http://localhost:5173 > /dev/null 2>&1 && echo "✅ Healthy" || echo "❌ Unhealthy"

echo ""
echo "============================================"
echo "📝 Recent Logs (last 5 lines each):"
echo "============================================"

echo ""
echo "🔹 APIs Container:"
docker-compose logs --tail=5 saga-apis 2>/dev/null | tail -5

echo ""
echo "🔹 Workers Container:"
docker-compose logs --tail=5 saga-workers 2>/dev/null | tail -5

echo ""
echo "============================================"
echo "✅ Status check complete!"
echo "============================================"
