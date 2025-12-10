#!/bin/bash
#
# HuggingHugh Nginx and SSL Setup
# Configures nginx for hugginghugh.etcbin.io with Let's Encrypt SSL
#

set -e

DOMAIN="hugginghugh.etcbin.io"
WEB_ROOT="/var/www/hugginghugh.etcbin.io"
NGINX_CONF="/etc/nginx/sites-available/$DOMAIN"
CERTBOT_ROOT="/var/www/certbot"

echo "=== HuggingHugh Nginx Setup ==="
echo "Domain: $DOMAIN"
echo "Web root: $WEB_ROOT"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo $0"
    exit 1
fi

# Step 1: Create web root directory
echo "[1/5] Creating web root directory..."
mkdir -p "$WEB_ROOT"
mkdir -p "$CERTBOT_ROOT"
chown -R www-data:www-data "$WEB_ROOT"
chmod -R 755 "$WEB_ROOT"
echo "  Created $WEB_ROOT"

# Step 2: Create initial nginx config (HTTP only for certbot)
echo "[2/5] Creating initial Nginx config..."
cat > "$NGINX_CONF" << 'NGINX_HTTP'
# HuggingHugh - HTTP only (for initial certbot)
server {
    listen 80;
    server_name hugginghugh.etcbin.io;

    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect everything else to HTTPS (after SSL is set up)
    location / {
        root /var/www/hugginghugh.etcbin.io;
        index index.html;
    }
}
NGINX_HTTP

# Enable the site
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
echo "  Nginx config created and enabled"

# Step 3: Test and reload nginx
echo "[3/5] Testing and reloading Nginx..."
nginx -t
systemctl reload nginx
echo "  Nginx reloaded"

# Step 4: Get SSL certificate
echo "[4/5] Obtaining SSL certificate..."
echo ""
echo "Running certbot..."
certbot certonly --webroot -w "$CERTBOT_ROOT" -d "$DOMAIN" --non-interactive --agree-tos --email admin@etcbin.io || {
    echo ""
    echo "NOTE: If certbot failed, ensure:"
    echo "  1. DNS for $DOMAIN points to this server"
    echo "  2. Port 80 is accessible from the internet"
    echo "  3. Run: certbot certonly --webroot -w $CERTBOT_ROOT -d $DOMAIN"
    echo ""
    echo "Continuing with HTTP-only config for now..."
}

# Step 5: Update nginx config with SSL (if cert exists)
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "[5/5] Updating Nginx config with SSL..."
    cat > "$NGINX_CONF" << 'NGINX_HTTPS'
# HuggingHugh - SBOM Dashboard for HuggingFace Models
# https://hugginghugh.etcbin.io

# HTTP - redirect to HTTPS
server {
    listen 80;
    server_name hugginghugh.etcbin.io;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name hugginghugh.etcbin.io;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/hugginghugh.etcbin.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hugginghugh.etcbin.io/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Root directory
    root /var/www/hugginghugh.etcbin.io;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Cache static assets
    location /static/ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Cache reports (but allow refresh)
    location /reports/ {
        expires 1d;
        add_header Cache-Control "public";
    }

    # API JSON files
    location /api/ {
        expires 1h;
        add_header Cache-Control "public";
        add_header Access-Control-Allow-Origin "*";
    }

    # Main location
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Error pages
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
NGINX_HTTPS

    nginx -t
    systemctl reload nginx
    echo "  SSL configuration applied"
else
    echo "[5/5] Skipping SSL config (certificate not found)"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Web root: $WEB_ROOT"
echo "Nginx config: $NGINX_CONF"
echo ""
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "Site accessible at: https://$DOMAIN"
else
    echo "Site accessible at: http://$DOMAIN"
    echo ""
    echo "To enable SSL later, run:"
    echo "  sudo certbot certonly --webroot -w $CERTBOT_ROOT -d $DOMAIN"
    echo "  sudo $0  # Re-run this script"
fi
echo ""
