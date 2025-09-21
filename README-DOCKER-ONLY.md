# RARSMS - Pure Docker Compose Deployment

For environments without Make, bash, or shell scripts (Synology NAS, minimal servers, etc.)

## 🚀 Quick Start (3 Commands)

```bash
# 1. Setup configuration files
docker compose --profile setup run --rm setup

# 2. Edit .env with your configuration
# (Use any text editor or web interface)

# 3. Start all services
docker compose up -d
```

**Access:** http://localhost:8090

## 📋 Step-by-Step Instructions

### Step 1: Initial Setup

Run the setup container to create configuration files:

```bash
docker compose --profile setup run --rm setup
```

This creates:
- `.env` file from `.env.example`
- `config/config.yaml` from example
- `data/pocketbase/` directory

### Step 2: Configure Your Environment

Edit the `.env` file with your actual values:

```bash
# Required Configuration
APRS_CALLSIGN=RARSMS
APRS_PASSCODE=12345                 # Calculate from your callsign
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_CHANNEL_ID=your_channel_id

# Email Configuration
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin@yourclub.org

# System URL
SYSTEM_URL=http://localhost:8090
```

### Step 3: Start Services

Start all RARSMS services:

```bash
docker compose up -d
```

### Step 4: Verify Installation

Check that services are running:

```bash
docker compose ps
```

You should see:
- ✅ `rarsms-pocketbase` (healthy)
- ✅ `rarsms-aprs` (running)
- ✅ `rarsms-discord` (running)

## 🛠️ Management Commands

### Essential Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View status
docker compose ps

# View logs (all services)
docker compose logs

# View logs (specific service)
docker compose logs pocketbase
docker compose logs aprs-connector
docker compose logs discord-bot

# Follow logs in real-time
docker compose logs -f

# Update and restart
docker compose build
docker compose up -d
```

### Service Management

```bash
# Restart specific service
docker compose restart pocketbase
docker compose restart aprs-connector
docker compose restart discord-bot

# View resource usage
docker stats

# Check service health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

## 🔧 Configuration Validation

### Check Configuration

```bash
# Validate Docker Compose file
docker compose config

# Test PocketBase health
curl http://localhost:8090/api/health

# Check environment variables
docker compose config | grep -A 50 environment
```

### Common Configuration Issues

**Missing environment variables:**
```bash
# Check if required vars are set
grep -E "APRS_PASSCODE|DISCORD_TOKEN|DISCORD_GUILD_ID|DISCORD_CHANNEL_ID" .env
```

**Port conflicts:**
```yaml
# Edit docker-compose.yml to change ports
services:
  pocketbase:
    ports:
      - "8091:8090"  # Use 8091 instead of 8090
```

## 📊 Monitoring & Logs

### Health Checks

```bash
# Check all container health
docker compose ps

# Detailed health status
docker inspect rarsms-pocketbase --format='{{.State.Health.Status}}'

# Service-specific checks
curl -f http://localhost:8090/api/health || echo "PocketBase unhealthy"
```

### Log Management

```bash
# View recent logs (last 50 lines)
docker compose logs --tail=50

# View logs for specific time period
docker compose logs --since "2024-01-01T10:00:00" --until "2024-01-01T11:00:00"

# Export logs to file
docker compose logs > rarsms-logs-$(date +%Y%m%d).txt

# View real-time logs
docker compose logs -f --tail=10
```

### Debugging

```bash
# Enter container for debugging
docker compose exec pocketbase sh
docker compose exec aprs-connector sh
docker compose exec discord-bot sh

# Run management commands
docker compose --profile management run --rm management sh

# Check network connectivity
docker compose exec aprs-connector ping pocketbase
docker compose exec discord-bot ping pocketbase
```

## 🔄 Updates & Maintenance

### Update RARSMS

```bash
# Pull latest code (if using git)
git pull

# Rebuild containers
docker compose build

# Restart with new images
docker compose up -d

# Clean up old images
docker image prune -f
```

### Backup & Restore

```bash
# Backup data
tar -czf rarsms-backup-$(date +%Y%m%d).tar.gz data/ config/ .env

# Backup database only
docker compose exec pocketbase tar -czf /tmp/pb-backup.tar.gz /app/pb_data
docker cp rarsms-pocketbase:/tmp/pb-backup.tar.gz ./pb-backup-$(date +%Y%m%d).tar.gz

# Restore from backup
docker compose down
tar -xzf rarsms-backup-YYYYMMDD.tar.gz
docker compose up -d
```

## 🔒 Security & Production

### Production Configuration

```bash
# Set production environment
LOG_LEVEL=info
EMAIL_DEV_MODE=false

# Use Docker secrets (advanced)
echo "your_discord_token" | docker secret create discord_token -
```

### Firewall Configuration

```bash
# Allow only necessary ports
# Port 8090 for web interface
# No other ports need external access
```

### SSL/TLS Setup

```yaml
# Use reverse proxy (nginx, traefik, etc.)
# Example nginx config:
server {
    listen 443 ssl;
    server_name rarsms.yourdomain.com;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🚨 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check Docker daemon
docker version

# Check compose file syntax
docker compose config

# Check logs for errors
docker compose logs
```

**Database connection errors:**
```bash
# Verify PocketBase is healthy
docker compose exec pocketbase wget -q --spider http://localhost:8090/api/health

# Check network connectivity
docker compose exec aprs-connector ping pocketbase
```

**Permission errors:**
```bash
# Fix file permissions
chmod 644 .env
chmod -R 755 data/
```

**Resource issues:**
```bash
# Check available resources
docker system df
docker stats

# Clean up unused resources
docker system prune -f
```

### Service-Specific Issues

**APRS Connector:**
```bash
# Check APRS connectivity
docker compose exec aprs-connector nc -zv rotate.aprs2.net 14580

# Verify passcode
# Calculate at: https://apps.magicbug.co.uk/passcode/
```

**Discord Bot:**
```bash
# Check bot permissions
# Verify token and channel IDs in .env

# Test bot connectivity
docker compose logs discord-bot | grep -i "logged in"
```

## 📱 Platform-Specific Notes

### Synology NAS
- Use Container Manager interface
- Upload files via File Station
- Configure firewall rules in DSM
- Set up DDNS for external access

### QNAP NAS
- Use Container Station
- Enable SSH if needed for file upload
- Configure port forwarding

### Unraid
- Use Community Applications
- Add as custom compose stack
- Configure reverse proxy if desired

### Cloud Platforms
- Works on any Docker-compatible platform
- AWS ECS, Google Cloud Run, Azure Container Instances
- Remember to configure external access and security groups

## ✅ Success Checklist

- [ ] `.env` file configured with real values
- [ ] All containers showing as healthy/running
- [ ] Web dashboard accessible at configured URL
- [ ] APRS connector shows online status
- [ ] Discord bot responds in channel
- [ ] Email notifications working (test user registration)
- [ ] Can create admin account and approve users
- [ ] End-to-end message test (APRS → Discord → APRS)

## 🎯 Next Steps

1. **Create Admin Account**: Visit web dashboard, register, approve via admin panel
2. **Test Messaging**: Send APRS message to RARSMS callsign
3. **Setup Monitoring**: Configure log monitoring and alerts
4. **Member Onboarding**: Share registration instructions with club members
5. **Backup Strategy**: Set up automated backups
6. **Production Hardening**: SSL, firewall, monitoring

Your RARSMS system is now ready for 24/7 amateur radio messaging! 📡