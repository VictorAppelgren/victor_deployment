#!/bin/bash
# SSL Certificate Setup for Saga
# Bulletproof version - handles nginx restart loops, missing configs, etc.

set -e
cd "$(dirname "$0")"

# Add domains here as you configure DNS for them
DOMAINS="sagalabs.world www.sagalabs.world"
EMAIL="admin@sagalabs.world"  # Change this to your email

echo "========================================"
echo "🔐 Saga SSL Certificate Setup"
echo "========================================"

# Get the docker-compose project name (used for volume naming)
PROJECT_NAME=$(docker compose config --format json 2>/dev/null | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="victor_deployment"
fi
CERT_VOLUME="${PROJECT_NAME}_certbot_certs"
WWW_VOLUME="${PROJECT_NAME}_certbot_www"

echo "Project: $PROJECT_NAME"
echo "Cert volume: $CERT_VOLUME"
echo "WWW volume: $WWW_VOLUME"
echo ""

# Check if certs already exist in the Docker volume
CERT_EXISTS=$(docker run --rm -v ${CERT_VOLUME}:/etc/letsencrypt alpine sh -c \
    "test -f /etc/letsencrypt/live/sagalabs.world/fullchain.pem && echo 'yes' || echo 'no'" 2>/dev/null || echo 'no')

if [ "$CERT_EXISTS" = "yes" ]; then
    echo "✅ SSL certificates already exist"
    echo ""
    echo "To force renewal, run:"
    echo "  docker run --rm -v ${CERT_VOLUME}:/etc/letsencrypt certbot/certbot renew --force-renewal"
    echo ""
    echo "To switch to SSL config:"
    echo "  cp nginx/nginx-ssl.conf nginx/nginx.conf"
    echo "  docker exec nginx nginx -s reload"
    exit 0
fi

# ============================================================
# Step 1: Ensure certbot-only nginx config exists
# ============================================================
echo "📝 Step 1: Setting up minimal nginx config..."

if [ ! -f nginx/nginx-certbot-only.conf ]; then
    echo "   Creating nginx-certbot-only.conf (no upstream dependencies)..."
    cat > nginx/nginx-certbot-only.conf << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    # Minimal config for certbot ONLY - no upstream dependencies
    server {
        listen 80;
        server_name localhost 167.172.185.204 sagalabs.world www.sagalabs.world;

        # ACME challenge for Let's Encrypt
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Everything else - simple response
        location / {
            return 200 'Certbot setup in progress. Server will be available shortly.';
            add_header Content-Type text/plain;
        }
    }
}
NGINX_EOF
    echo "   ✅ Created nginx-certbot-only.conf"
else
    echo "   ✅ nginx-certbot-only.conf exists"
fi

# Backup current config if it exists and isn't the certbot one
if [ -f nginx/nginx.conf ]; then
    if ! diff -q nginx/nginx.conf nginx/nginx-certbot-only.conf > /dev/null 2>&1; then
        cp nginx/nginx.conf nginx/nginx.conf.pre-certbot-backup
        echo "   📦 Backed up current nginx.conf"
    fi
fi

# Use certbot-only config
cp nginx/nginx-certbot-only.conf nginx/nginx.conf
echo "   ✅ Switched to certbot-only config"

# ============================================================
# Step 2: Stop nginx completely and restart fresh
# ============================================================
echo ""
echo "🔄 Step 2: Restarting nginx with minimal config..."

# Stop nginx completely (might be in restart loop)
docker compose stop nginx 2>/dev/null || true
sleep 2

# Remove the container to clear any bad state
docker compose rm -f nginx 2>/dev/null || true

# Start nginx fresh - use --no-deps to avoid waiting for unhealthy containers
docker compose up -d nginx --no-deps
sleep 3

# Verify nginx is actually running (not restarting)
NGINX_STATUS=$(docker compose ps nginx --format json 2>/dev/null | grep -o '"State":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
if [ "$NGINX_STATUS" = "running" ]; then
    echo "   ✅ Nginx is running"
else
    echo "   ⚠️  Nginx status: $NGINX_STATUS"
    echo "   Checking logs..."
    docker compose logs --tail=10 nginx
    echo ""
    echo "   Trying one more restart..."
    docker compose restart nginx
    sleep 3
fi

# Test that port 80 responds
echo "   Testing HTTP response..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "   ✅ Port 80 is responding"
else
    echo "   ⚠️  Port 80 not responding locally, but might work externally"
fi

# ============================================================
# Step 3: Request certificates
# ============================================================
echo ""
echo "🔐 Step 3: Requesting SSL certificates..."
echo "   Domains: $DOMAINS"
echo "   Email: $EMAIL"
echo ""

DOMAIN_ARGS=""
for domain in $DOMAINS; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

# Run certbot
docker run --rm \
    -v ${CERT_VOLUME}:/etc/letsencrypt \
    -v ${WWW_VOLUME}:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    $DOMAIN_ARGS

# Check if certs were created
CERT_CREATED=$(docker run --rm -v ${CERT_VOLUME}:/etc/letsencrypt alpine sh -c \
    "test -f /etc/letsencrypt/live/sagalabs.world/fullchain.pem && echo 'yes' || echo 'no'" 2>/dev/null || echo 'no')

if [ "$CERT_CREATED" != "yes" ]; then
    echo ""
    echo "❌ Certificate creation failed!"
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure DNS for $DOMAINS points to this server"
    echo "2. Check that port 80 is accessible from the internet"
    echo "3. Run: curl -I http://sagalabs.world/.well-known/acme-challenge/test"
    echo ""
    echo "The nginx config is still set to certbot-only mode."
    echo "Re-run this script after fixing the issue."
    exit 1
fi

echo "   ✅ Certificates created successfully!"

# ============================================================
# Step 4: Switch to SSL config
# ============================================================
echo ""
echo "🔄 Step 4: Switching to SSL nginx config..."

if [ ! -f nginx/nginx-ssl.conf ]; then
    echo "   ❌ nginx-ssl.conf not found!"
    echo "   Please create nginx/nginx-ssl.conf and run:"
    echo "     cp nginx/nginx-ssl.conf nginx/nginx.conf"
    echo "     docker exec nginx nginx -s reload"
    exit 1
fi

cp nginx/nginx-ssl.conf nginx/nginx.conf
echo "   ✅ Switched to SSL config"

# Reload nginx
docker exec nginx nginx -s reload
echo "   ✅ Nginx reloaded"

# Clean up backup
rm -f nginx/nginx.conf.pre-certbot-backup

# ============================================================
# Done!
# ============================================================
echo ""
echo "========================================"
echo "✅ SSL Setup Complete!"
echo "========================================"
echo ""
echo "Your site is now available at:"
echo "   https://sagalabs.world"
echo "   https://www.sagalabs.world"
echo ""
echo "Certificate renewal will be handled automatically by the certbot container."
echo ""
