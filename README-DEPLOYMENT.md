# RARSMS Deployment Guide

This guide covers deploying RARSMS on various platforms without requiring bash or shell scripts.

## 🚀 Quick Start (Any Platform)

RARSMS uses **Docker Compose** and **Make** for platform-independent deployment:

```bash
# 1. Clone and setup
git clone <repository-url>
cd rarsms

# 2. Configure (creates .env if needed)
make setup

# 3. Edit configuration
# Edit .env with your actual values
# Edit config/config.yaml if needed

# 4. Start system
make start
```

**Access Points:**
- 🌐 Web Dashboard: http://localhost:8090
- 📊 Admin Panel: http://localhost:8090/_/

## 📋 Available Commands

```bash
make help        # Show all available commands
make setup       # Initial configuration and validation
make start       # Start all services
make stop        # Stop all services
make restart     # Restart all services
make status      # Show service status and health
make logs        # View logs from all services
make build       # Build Docker images
make clean       # Remove all containers and data (destructive)

# Service-specific logs
make logs-aprs     # APRS connector logs
make logs-discord  # Discord bot logs
make logs-db       # PocketBase database logs
```

## 🖥️ Platform-Specific Instructions

### Windows
```cmd
# Install Docker Desktop
# Install Make for Windows or use Docker commands directly

# With Make
make setup
make start

# Without Make (direct Docker Compose)
docker compose up -d
```

### macOS
```bash
# Install Docker Desktop
# Make is usually pre-installed

make setup
make start
```

### Linux (Ubuntu/Debian)
```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose-plugin make

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in

make setup
make start
```

### Linux (RHEL/CentOS/Fedora)
```bash
# Install Docker and Docker Compose
sudo dnf install docker docker-compose make
sudo systemctl enable --now docker

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in

make setup
make start
```

### Cloud Servers (No Make)

If `make` is not available, use Docker Compose directly:

```bash
# 1. Setup configuration
cp .env.example .env
cp config/config.example.yaml config/config.yaml
mkdir -p data/pocketbase

# 2. Edit .env with your values
nano .env  # or vim, emacs, etc.

# 3. Build and start
docker compose build
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs
```

## ⚙️ Configuration

### Required Environment Variables (.env)

```bash
# APRS Configuration (REQUIRED)
APRS_CALLSIGN=RARSMS
APRS_PASSCODE=12345                 # Calculate from your callsign

# Discord Configuration (REQUIRED)
DISCORD_TOKEN=your_bot_token        # Discord bot token
DISCORD_GUILD_ID=123456789          # Your Discord server ID
DISCORD_CHANNEL_ID=987654321        # Target channel ID

# Email Configuration (REQUIRED for user approval)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin1@club.org,admin2@club.org

# Optional Settings
LOG_LEVEL=info                      # debug, info, warn, error
SYSTEM_URL=http://localhost:8090    # For email links
```

### Getting Configuration Values

1. **APRS Passcode**: Calculate at https://apps.magicbug.co.uk/passcode/
2. **Discord Bot**: https://discord.com/developers/applications
3. **Discord IDs**: Enable Developer Mode → Right-click → Copy ID

## 🐳 Docker Deployment Options

### Standard Deployment
```bash
docker compose up -d
```

### Development Mode
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Production with Custom Config
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 🌐 Production Deployment

### Reverse Proxy Setup (Nginx)

```nginx
# /etc/nginx/sites-available/rarsms
server {
    listen 80;
    server_name rarsms.yourdomain.com;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d rarsms.yourdomain.com
```

### Environment Security
```bash
# Set proper permissions on .env
chmod 600 .env

# Use Docker secrets for production
docker swarm init
echo "your_discord_token" | docker secret create discord_token -
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Quick status check
make status

# Detailed service info
docker compose ps
docker compose top

# Resource usage
docker stats
```

### Log Management
```bash
# View recent logs
make logs

# Follow logs in real-time
docker compose logs -f

# Service-specific logs
docker compose logs pocketbase
docker compose logs aprs-connector
docker compose logs discord-bot
```

### Backup
```bash
# Backup database
docker compose exec pocketbase cp -r /app/pb_data /app/backup
docker cp rarsms-pocketbase:/app/backup ./backup-$(date +%Y%m%d)

# Backup configuration
tar -czf rarsms-config-$(date +%Y%m%d).tar.gz .env config/
```

### Updates
```bash
# Pull latest code
git pull

# Rebuild and restart
make build
make restart

# Or with Docker Compose directly
docker compose build
docker compose up -d
```

## 🔧 Troubleshooting

### Common Issues

**Port 8090 already in use:**
```bash
# Change port in docker-compose.yml
ports:
  - "8091:8090"  # Use 8091 instead
```

**Permission denied:**
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
# Log out and back in
```

**Configuration errors:**
```bash
# Validate configuration
docker compose config

# Check logs for errors
make logs
```

**Services not starting:**
```bash
# Check individual service logs
docker compose logs pocketbase
docker compose logs aprs-connector
docker compose logs discord-bot

# Restart specific service
docker compose restart pocketbase
```

### Getting Help

1. Check service status: `make status`
2. View logs: `make logs`
3. Validate config: `docker compose config`
4. Test connectivity: `curl http://localhost:8090/api/health`

## 🔒 Security Considerations

- **Firewall**: Only expose port 8090 (or your custom port)
- **Authentication**: Use strong passwords for admin accounts
- **HTTPS**: Use reverse proxy with SSL in production
- **Updates**: Keep Docker images and base system updated
- **Backups**: Regular database and configuration backups
- **Monitoring**: Set up log monitoring and alerting

## 📝 Production Checklist

- [ ] Configure proper SMTP credentials
- [ ] Set strong admin passwords
- [ ] Configure reverse proxy with SSL
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Test disaster recovery procedures
- [ ] Set up monitoring and alerting
- [ ] Document operational procedures