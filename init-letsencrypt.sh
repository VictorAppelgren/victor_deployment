#!/bin/bash
# SSL Certificate Setup for Saga
# Only requests new certs if they don't exist

set -e
cd "$(dirname "$0")"

# Add domains here as you configure DNS for them
DOMAINS="sagalabs.world www.sagalabs.world"
EMAIL="admin@sagalabs.world"  # Change this to your email

# Get the docker-compose project name (used for volume naming)
PROJECT_NAME=$(docker compose config --format json 2>/dev/null | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="victor_deployment"
fi
CERT_VOLUME="${PROJECT_NAME}_certbot_certs"
WWW_VOLUME="${PROJECT_NAME}_certbot_www"

# Check if certs already exist in the Docker volume
CERT_EXISTS=$(docker run --rm -v ${CERT_VOLUME}:/etc/letsencrypt alpine sh -c \
    "test -f /etc/letsencrypt/live/sagalabs.world/fullchain.pem && echo 'yes' || echo 'no'" 2>/dev/null || echo 'no')

if [ "$CERT_EXISTS" = "yes" ]; then
    echo "✅ SSL certificates already exist"
    echo "To force renewal, run: docker run --rm -v ${CERT_VOLUME}:/etc/letsencrypt certbot/certbot renew --force-renewal"
    exit 0
fi

echo "🔐 Requesting SSL certificates for: $DOMAINS"

# Step 1: Use HTTP-only config temporarily (nginx must serve ACME challenge)
echo "📝 Switching to HTTP-only nginx config..."
cp nginx/nginx.conf nginx/nginx.conf.bak
cp nginx/nginx-http-only.conf nginx/nginx.conf

# Step 2: Reload nginx config (assumes nginx is already running)
echo "🔄 Reloading nginx config..."
docker exec nginx nginx -s reload || docker compose up -d --no-deps nginx
sleep 2

# Step 3: Request certificates using webroot mode
echo "🔐 Requesting certificates..."
DOMAIN_ARGS=""
for domain in $DOMAINS; do
    DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

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

# Step 4: Switch to SSL config and reload nginx
echo "🔄 Switching to SSL nginx config..."
rm -f nginx/nginx.conf.bak
cp nginx/nginx-ssl.conf nginx/nginx.conf
docker exec nginx nginx -s reload

echo "✅ Done! Your site should now be available via HTTPS"
echo "   https://sagalabs.world"
echo "   https://www.sagalabs.world"
