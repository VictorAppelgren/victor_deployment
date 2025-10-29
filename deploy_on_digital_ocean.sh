#!/bin/bash
# Saga Graph - Complete Server Setup & Deployment
# Run this AFTER you've pulled all 4 repos into /opt/saga-graph/

set -e  # Exit on any error

echo "🚀 Saga Graph - Server Setup & Deployment"
echo ""

# Check we're in the right directory
if [ ! -f "docker compose.yml" ]; then
    echo "❌ Error: docker compose.yml not found!"
    echo "Please run this script from the deployment directory:"
    echo "  cd /opt/saga-graph/deployment"
    echo "  ./deploy.sh"
    exit 1
fi

# Step 1: Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y
apt install -y curl wget htop ncdu

# Step 2: Verify Docker is installed
echo "🐳 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

docker --version
docker compose version

# Step 3: Verify .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file in deployment directory before running this script."
    exit 1
fi
echo "✅ .env file found"

# Step 4: Configure firewall
echo "🔒 Configuring firewall..."
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS (future)
ufw allow 7687/tcp  # Neo4j Bolt
ufw allow 7474/tcp  # Neo4j Browser
echo "✅ Firewall configured"

# Step 5: Build Docker images
echo "🏗️  Building Docker images (this takes 5-10 minutes)..."
docker compose build --no-cache --pull

# Step 6: Start all services
echo "🚀 Starting all services..."
docker compose up -d

# Step 7: Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 15

# Step 8: Show status
echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Container Status:"
docker compose ps
echo ""

# Get server IP
SERVER_IP=$(curl -s ifconfig.me)

echo "🌐 Access your application:"
echo "  Frontend: http://${SERVER_IP}/"
echo "  Login:    http://${SERVER_IP}/login"
echo "  Neo4j:    http://${SERVER_IP}/neo4j"
echo ""
echo "🔑 API Key for testing:"
echo "  785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12"
echo ""
echo "👤 Login credentials:"
echo "  Username: Victor"
echo "  Password: v123"
echo ""
echo "📝 View logs:"
echo "  docker compose logs -f"
echo ""
echo "🧪 Test from your Mac:"
echo "  export SERVER_IP=${SERVER_IP}"
echo "  curl http://\$SERVER_IP/api/health -H \"X-API-Key: 785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12\""
echo ""
echo "🎉 Done! Open http://${SERVER_IP}/login in your browser"
