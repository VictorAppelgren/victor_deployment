#!/bin/bash
# Smart startup: Start all services (bootstrap runs automatically in main.py if needed)

set -e

echo "============================================"
echo "🚀 SAGA STACK STARTUP"
echo "============================================"
echo ""

# Start Neo4j first
echo "1️⃣  Starting Neo4j..."
docker-compose up -d neo4j

# Wait for Neo4j to be ready
echo "2️⃣  Waiting for Neo4j to be ready..."
echo "   (this takes ~30-60 seconds)"
for i in {1..60}; do
    if docker exec saga-neo4j wget -q --spider http://localhost:7474 2>/dev/null; then
        echo "   ✅ Neo4j is ready!"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Start all services (bootstrap will run automatically in main.py if needed)
echo "3️⃣  Starting all services..."
docker-compose up -d

echo ""
echo "============================================"
echo "✅ SAGA STACK RUNNING"
echo "============================================"
echo ""
echo "📊 Check status:"
echo "   docker-compose ps"
echo ""
echo "📋 View logs:"
echo "   docker-compose logs -f"
echo "   docker-compose logs -f saga-workers"
echo "   docker-compose logs -f saga-apis"
echo ""
echo "🌐 Access points:"
echo "   Frontend:  http://localhost"
echo "   Neo4j:     http://localhost:7474"
echo "   Backend:   http://localhost:8000"
echo ""
