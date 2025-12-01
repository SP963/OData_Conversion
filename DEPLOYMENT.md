# AWS EC2 Deployment Guide - TRP API

## Prerequisites
- AWS EC2 instance (Ubuntu 22.04 LTS recommended)
- RDS PostgreSQL instance
- Security groups configured for EC2 and RDS
- SSH key pair for EC2 access

## Step 1: EC2 Instance Setup

### Connect to EC2
```bash
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

### Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Install dependencies
```bash
sudo apt install -y python3-pip python3-venv git nginx supervisor
```

## Step 2: Clone and Setup Application

### Clone repository
```bash
cd /opt
sudo git clone <your-repo-url> trp-api
sudo chown -R ubuntu:ubuntu trp-api
cd trp-api
```

### Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure environment
```bash
cp .env.example .env
nano .env  # Edit with your RDS credentials and API credentials
```

**Important**: Update the following in `.env`:
- `DATABASE_URL` - your RDS endpoint
- `PGHOST`, `PGUSER`, `PGPASSWORD` - RDS credentials
- `API_BASIC_USER`, `API_BASIC_PASS` - Your API credentials

### Verify database connection
```bash
python3 -c "from app_basic_auth import engine; engine.connect(); print('DB Connection OK')"
```

## Step 3: Configure Gunicorn with Supervisor

### Create supervisor configuration
```bash
sudo nano /etc/supervisor/conf.d/trp-api.conf
```

**Paste the following content:**
```ini
[program:trp-api]
directory=/opt/trp-api
command=/opt/trp-api/venv/bin/gunicorn \
    --config /opt/trp-api/gunicorn_config.py \
    app_basic_auth:app
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/trp-api/gunicorn.log
```

### Create log directory
```bash
sudo mkdir -p /var/log/trp-api /var/log/gunicorn /var/run/gunicorn
sudo chown ubuntu:ubuntu /var/log/trp-api /var/log/gunicorn /var/run/gunicorn
```

### Start supervisor
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start trp-api
```

### Verify service
```bash
sudo supervisorctl status trp-api
```

## Step 4: Configure Nginx Reverse Proxy

### Create nginx configuration
```bash
sudo nano /etc/nginx/sites-available/trp-api
```

**Paste the following content:**
```nginx
upstream trp_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP
    
    client_max_body_size 100M;

    location / {
        proxy_pass http://trp_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://trp_api;
        access_log off;
    }
}
```

### Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/trp-api /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

## Step 5: SSL Configuration (HTTPS)

### Install Certbot
```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Get SSL certificate
```bash
sudo certbot --nginx -d your-domain.com
```

## Step 6: AWS Security Groups Configuration

### EC2 Security Group - Inbound Rules
- **HTTP (80)** - Source: 0.0.0.0/0
- **HTTPS (443)** - Source: 0.0.0.0/0
- **SSH (22)** - Source: Your IP (or restricted)

### RDS Security Group - Inbound Rules
- **PostgreSQL (5432)** - Source: EC2 Security Group ID

## Step 7: Monitoring and Maintenance

### View logs
```bash
# Gunicorn logs
tail -f /var/log/trp-api/gunicorn.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Supervisor status
sudo supervisorctl status
```

### Check application health
```bash
curl -u admin:your_password http://localhost/health
```

### Restart application
```bash
sudo supervisorctl restart trp-api
```

## Step 8: Auto-start on Reboot

### Enable supervisor
```bash
sudo systemctl enable supervisor
```

### Verify services start on boot
```bash
sudo systemctl is-enabled supervisor
sudo systemctl is-enabled nginx
```

## Database Backup (Optional)

### Create backup script
```bash
cat > /opt/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/db-backups"
mkdir -p $BACKUP_DIR
pg_dump -h $PGHOST -U $PGUSER $PGDATABASE | gzip > $BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).sql.gz
find $BACKUP_DIR -type f -mtime +7 -delete  # Keep 7 days
EOF
chmod +x /opt/backup-db.sh
```

### Schedule with cron
```bash
crontab -e
# Add: 0 2 * * * /opt/backup-db.sh
```

## Important Security Notes

1. **Never commit .env to git** - Use `.env.example` template
2. **Update RDS security group** to only allow EC2 access
3. **Change default API credentials** in production
4. **Use AWS Secrets Manager** for sensitive data (advanced)
5. **Enable CloudWatch monitoring** for EC2 and RDS
6. **Configure auto-scaling** if needed
7. **Enable RDS automated backups** in AWS Console

## Troubleshooting

### Service won't start
```bash
sudo supervisorctl tail trp-api stderr
```

### Database connection failed
```bash
# Test RDS connectivity
nc -zv your-rds-endpoint.rds.amazonaws.com 5432
```

### Port already in use
```bash
sudo lsof -i :8000
```

### SSL certificate issues
```bash
sudo certbot renew --dry-run
```

## Useful Commands

```bash
# Monitor application in real-time
watch -n 5 'sudo supervisorctl status'

# Check system resources
free -h
df -h
htop

# View full gunicorn process
ps aux | grep gunicorn

# Restart all services
sudo supervisorctl restart all && sudo systemctl restart nginx
```
