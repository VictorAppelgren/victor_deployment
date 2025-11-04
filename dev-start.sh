#!/bin/bash
# Local Development Startup
# Starts: Neo4j, Backend, Frontend, NGINX
# You manually run: main.py and main_top_sources.py

set -e

echo "🚀 Starting SAGA Graph Local Dev Environment"
echo ""

# Start all services except workers
docker compose up -d \
  neo4j \
  saga-apis \
  frontend \
  nginx

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

echo ""
echo "✅ Dev environment ready!"
echo ""
echo "📊 Services:"
echo "  Neo4j:    http://localhost:7474"
echo "  App:      http://localhost"
echo ""
echo "📖 See DEV_README.md for:"
echo "  - Rebuild commands"
echo "  - View logs"
echo "  - Troubleshooting"
echo ""
echo "▶️  Run your workers:"
echo "  cd saga-graph && python main.py"
echo ""
echo "🛑 Stop: docker compose down"
