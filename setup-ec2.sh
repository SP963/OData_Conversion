#!/bin/bash

# TRP API - AWS EC2 Quick Setup Script
# Usage: bash setup-ec2.sh

set -e

echo "================================"
echo "TRP API - AWS EC2 Setup"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as non-root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run this script as root. Use 'sudo' for specific commands.${NC}"
   exit 1
fi

echo -e "${YELLOW}Step 1: Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3-pip python3-venv git nginx supervisor

echo -e "${YELLOW}Step 2: Creating application directory...${NC}"
sudo mkdir -p /opt/trp-api
sudo chown -R $USER:$USER /opt/trp-api

echo -e "${YELLOW}Step 3: Setting up Python virtual environment...${NC}"
cd /opt/trp-api
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}Step 4: Installing Python dependencies...${NC}"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo -e "${YELLOW}Step 5: Creating .env file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}IMPORTANT: Edit .env with your RDS credentials${NC}"
    echo "nano /opt/trp-api/.env"
else
    echo "✓ .env file already exists"
fi

echo -e "${YELLOW}Step 6: Creating log directories...${NC}"
sudo mkdir -p /var/log/trp-api /var/log/gunicorn /var/run/gunicorn
sudo chown $USER:$USER /var/log/trp-api /var/log/gunicorn /var/run/gunicorn
sudo chmod 755 /var/log/trp-api /var/log/gunicorn

echo -e "${YELLOW}Step 7: Setting up Supervisor configuration...${NC}"
sudo cp supervisor-trp-api.conf /etc/supervisor/conf.d/trp-api.conf
sudo supervisorctl reread
sudo supervisorctl update

echo -e "${YELLOW}Step 8: Setting up Nginx configuration...${NC}"
sudo cp nginx-trp-api.conf /etc/nginx/sites-available/trp-api
sudo ln -sf /etc/nginx/sites-available/trp-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo -e "${YELLOW}Step 9: Testing database connection...${NC}"
source venv/bin/activate
python3 << EOF
import os
os.chdir('/opt/trp-api')
from app_basic_auth import engine
try:
    with engine.connect() as conn:
        conn.execute(conn.dialect.identifier_preparer.quote("SELECT 1"))
    print("✓ Database connection successful!")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    exit(1)
EOF

echo -e "${YELLOW}Step 10: Starting services...${NC}"
sudo supervisorctl start trp-api
sleep 2
sudo supervisorctl status trp-api

echo ""
echo -e "${GREEN}================================"
echo "Setup Complete!"
echo "================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your RDS credentials:"
echo "   nano /opt/trp-api/.env"
echo ""
echo "2. Update Nginx configuration with your domain/IP:"
echo "   sudo nano /etc/nginx/sites-available/trp-api"
echo "   Then: sudo systemctl reload nginx"
echo ""
echo "3. Test the API:"
echo "   curl -u admin:password http://localhost/health"
echo ""
echo "4. (Optional) Set up SSL with Certbot:"
echo "   sudo apt install certbot python3-certbot-nginx"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "5. Monitor logs:"
echo "   tail -f /var/log/trp-api/gunicorn.log"
echo ""
