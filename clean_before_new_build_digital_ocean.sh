#!/bin/bash
# Clean all Docker images and containers

set -e  # Exit on any error

echo "🧹 Cleaning Docker environment..."

# Stop and remove all containers
echo "⏹️  Stopping containers..."
docker-compose down --remove-orphans

# Remove project images
echo "🗑️  Removing images..."
docker rmi deployment-saga-apis deployment-frontend deployment-saga-worker-main -f 2>/dev/null || true

# Clean build cache
echo "🧼 Cleaning build cache..."
docker builder prune -f

echo ""
echo "✅ Clean complete!"
echo ""
echo "Run ./deploy_on_digital_ocean.sh to rebuild"
