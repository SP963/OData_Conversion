# AWS EC2 Deployment Checklist

## Pre-Deployment
- [ ] AWS Account set up with appropriate IAM permissions
- [ ] EC2 instance created (Ubuntu 22.04 LTS recommended)
- [ ] RDS PostgreSQL instance created and configured
- [ ] Security groups configured for EC2 and RDS
- [ ] SSH key pair created and stored securely
- [ ] Domain name purchased (optional, can use EC2 IP)

## EC2 Instance Setup
- [ ] Connected to EC2 via SSH
- [ ] System packages updated (`apt update && apt upgrade`)
- [ ] Python 3 and dependencies installed
- [ ] Git installed for cloning repository

## Application Setup
- [ ] Repository cloned to `/opt/trp-api`
- [ ] Python virtual environment created
- [ ] Requirements installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example` template
- [ ] Database credentials correctly entered in `.env`
- [ ] API credentials (`API_BASIC_USER`, `API_BASIC_PASS`) configured
- [ ] Database connection tested successfully

## Service Configuration
- [ ] Gunicorn configuration reviewed and customized
- [ ] Supervisor installed and configured
- [ ] Supervisor service file created at `/etc/supervisor/conf.d/trp-api.conf`
- [ ] Supervisor service started and verified running
- [ ] Nginx installed and configured
- [ ] Nginx configuration file updated with correct domain/IP
- [ ] Nginx reloaded and verified
- [ ] Application accessible via Nginx reverse proxy

## Security Setup
- [ ] `.env` file permissions restricted (`chmod 600 .env`)
- [ ] SSH key permissions restricted (`chmod 400 key.pem`)
- [ ] EC2 security group allows only necessary ports
  - [ ] SSH (22) from restricted IPs
  - [ ] HTTP (80) from 0.0.0.0/0
  - [ ] HTTPS (443) from 0.0.0.0/0
- [ ] RDS security group allows PostgreSQL (5432) only from EC2 instance
- [ ] Firewall rules configured at OS level (if using UFW)

## SSL/HTTPS Setup (Recommended)
- [ ] Certbot installed
- [ ] SSL certificate generated for domain
- [ ] Nginx configuration updated with SSL settings
- [ ] HTTP to HTTPS redirect configured
- [ ] Certificate auto-renewal configured

## Monitoring & Logging
- [ ] Log directories created with correct permissions
- [ ] Gunicorn logs being written correctly
- [ ] Nginx logs accessible
- [ ] Supervisor logs configured
- [ ] CloudWatch agent installed (optional)
- [ ] Monitoring alerts set up in AWS Console

## Database
- [ ] RDS automated backups enabled (7-30 days retention)
- [ ] Database schema applied (TRP table created)
- [ ] Sample data loaded (if applicable)
- [ ] Backup script created and tested
- [ ] Backup cron job scheduled (if applicable)

## Application Testing
- [ ] Health check endpoint responds: `curl http://localhost/health-check`
- [ ] Authenticated endpoint responds: `curl -u admin:password http://localhost/health`
- [ ] API endpoints can be accessed (GET, POST, PUT, DELETE)
- [ ] Database read/write operations working
- [ ] Error handling working correctly

## Auto-Start & Restart
- [ ] Supervisor configured to start on boot
- [ ] Nginx configured to start on boot
- [ ] Application restarts automatically on failure
- [ ] Services verified to start after EC2 reboot

## Documentation
- [ ] Deployment guide updated for team
- [ ] API documentation generated and shared
- [ ] Crisis procedures documented (how to restart, rollback, etc.)
- [ ] Credentials stored securely (AWS Secrets Manager)
- [ ] Architecture diagram updated

## Production Hardening
- [ ] CORS settings restricted to specific domains
- [ ] Rate limiting configured (if applicable)
- [ ] Input validation tested
- [ ] SQL injection protection verified
- [ ] XSS protection enabled in headers
- [ ] CSRF protection configured (if applicable)

## Performance
- [ ] Gunicorn worker count optimized
- [ ] Connection pooling configured
- [ ] Database indexes created
- [ ] Query performance tested
- [ ] Load testing performed (if applicable)

## Ongoing Maintenance
- [ ] Monitoring dashboard set up
- [ ] Log rotation configured
- [ ] Update schedule planned
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented

## Final Verification
- [ ] Application accessible via domain/IP
- [ ] All CRUD operations working
- [ ] Authentication working
- [ ] SSL/HTTPS working (if configured)
- [ ] Logs are being collected properly
- [ ] System performs under expected load
- [ ] Database backups are happening
- [ ] Team trained on deployment and management

---

## Quick Deployment Command

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone and run setup script
git clone <your-repo-url> /opt/trp-api
cd /opt/trp-api
bash setup-ec2.sh

# Configure environment
nano .env

# Edit nginx config
sudo nano /etc/nginx/sites-available/trp-api

# Restart services
sudo supervisorctl restart trp-api
sudo systemctl reload nginx
```

## Support & Troubleshooting

- **Issue**: Service won't start - Check: `sudo supervisorctl tail trp-api stderr`
- **Issue**: Database connection fails - Check RDS security group and credentials
- **Issue**: Port already in use - Check: `sudo lsof -i :8000`
- **Issue**: Nginx errors - Check: `sudo nginx -t`
- **Issue**: SSL certificate issues - Check: `sudo certbot renew --dry-run`
