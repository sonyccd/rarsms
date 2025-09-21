# RARSMS on Synology NAS

Complete guide for deploying RARSMS on Synology NAS using Container Manager (Docker).

## 🏠 Why Synology NAS?

Perfect for amateur radio clubs:
- **24/7 Operation**: Always-on home server
- **Low Power**: Efficient operation
- **Web Interface**: Easy management via Synology DSM
- **Backup**: Built-in backup and redundancy
- **Remote Access**: VPN and remote management

## 📋 Prerequisites

### Synology Requirements
- **DSM 7.0+** with Container Manager package
- **2GB+ RAM** (4GB recommended)
- **1GB+ free space** for containers and data
- **Network**: Static IP or DDNS setup

### Configuration Needed
- Amateur radio license with valid callsign
- Discord server with bot permissions
- Email account for SMTP notifications

## 🚀 Installation Steps

### Step 1: Enable Container Manager

1. Open **Package Center** in DSM
2. Search for **Container Manager**
3. Install Container Manager
4. Open Container Manager after installation

### Step 2: Upload Project Files

**Option A: Git (if available)**
```bash
# SSH to Synology (enable SSH in Control Panel)
ssh admin@your-synology-ip
cd /volume1/docker  # or your preferred path
git clone <repository-url> rarsms
```

**Option B: File Upload**
1. Download RARSMS as ZIP from repository
2. Extract to your computer
3. Use **File Station** to upload to `/docker/rarsms/`
4. Ensure all files are uploaded correctly

### Step 3: Setup Configuration

1. Navigate to your RARSMS folder in File Station
2. Copy `.env.example` to `.env`
3. Edit `.env` with Text Editor (or download, edit, re-upload):

```bash
# Required Configuration
APRS_CALLSIGN=RARSMS
APRS_PASSCODE=12345                 # Calculate from your callsign
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_CHANNEL_ID=your_channel_id

# Email for user approvals
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin@yourclub.org

# Synology-specific
SYSTEM_URL=http://your-synology-ip:8090  # or DDNS name
```

4. Copy `config/config.example.yaml` to `config/config.yaml`

### Step 4: Run Setup (Optional)

If you want to validate configuration:

1. In Container Manager, go to **Project**
2. Click **Create**
3. Enter project name: `rarsms-setup`
4. Select your RARSMS folder
5. In the compose file, add:
```yaml
version: '3.8'
services:
  setup:
    image: alpine:latest
    volumes:
      - .:/app
    working_dir: /app
    command: |
      sh -c "
        cp .env.example .env 2>/dev/null || true
        cp config/config.example.yaml config/config.yaml 2>/dev/null || true
        mkdir -p data/pocketbase
        echo 'Setup complete. Edit .env and deploy main project.'
      "
```
6. Run once, then delete this project

### Step 5: Deploy RARSMS

1. In Container Manager, go to **Project**
2. Click **Create**
3. **Project Settings:**
   - **Project name**: `rarsms`
   - **Path**: Select your RARSMS folder
   - **Source**: Existing compose file
4. The `docker-compose.yml` will be automatically detected
5. Click **Next** and review settings
6. Click **Done** to deploy

### Step 6: Verify Deployment

1. In Container Manager, select the **rarsms** project
2. Check that all 3 containers are running:
   - `rarsms-pocketbase` (green/healthy)
   - `rarsms-aprs` (green/running)
   - `rarsms-discord` (green/running)

3. **Access Web Dashboard:**
   - URL: `http://your-synology-ip:8090`
   - Admin: `http://your-synology-ip:8090/_/`

## 🔧 Synology-Specific Configuration

### Port Configuration

If port 8090 conflicts with DSM services:

1. Edit `docker-compose.yml` in File Station
2. Change the ports section:
```yaml
ports:
  - "8091:8090"  # Use 8091 instead
```
3. Update project in Container Manager

### Firewall Settings

1. Go to **Control Panel** → **Security** → **Firewall**
2. Add rule for port 8090 (or your custom port)
3. Allow access from your network

### DDNS Setup (External Access)

1. **Control Panel** → **External Access** → **DDNS**
2. Set up DDNS (Synology, No-IP, etc.)
3. Update `.env` file:
```bash
SYSTEM_URL=https://yourname.synology.me:8090
```

### Reverse Proxy (Optional)

For cleaner URLs, use DSM's reverse proxy:

1. **Control Panel** → **Application Portal** → **Reverse Proxy**
2. Create new rule:
   - **Description**: RARSMS
   - **Source**: External port 80/443
   - **Destination**: localhost:8090

## 📊 Management via Container Manager

### View Logs
1. Container Manager → Project → **rarsms**
2. Select container (pocketbase, aprs, discord)
3. Click **Details** → **Log** tab

### Restart Services
1. Container Manager → Project → **rarsms**
2. Click **Action** → **Stop**
3. Click **Action** → **Start**

### Update RARSMS
1. Upload new files via File Station
2. Container Manager → Project → **rarsms**
3. Click **Action** → **Build**
4. Click **Action** → **Start**

### Backup Configuration
1. File Station → Right-click RARSMS folder
2. **Compress** → Create backup ZIP
3. Store backup in safe location

## 🔍 Troubleshooting

### Common Issues

**Containers won't start:**
- Check `.env` file has required values
- Verify file permissions (should be readable)
- Check Synology system resources

**Can't access web interface:**
- Verify port 8090 is not blocked by firewall
- Check if port conflicts with other services
- Try accessing via Synology's local IP

**APRS not connecting:**
- Verify APRS_PASSCODE is correct
- Check internet connectivity from NAS
- Ensure no firewall blocking outbound port 14580

**Discord bot offline:**
- Verify DISCORD_TOKEN is valid
- Check bot permissions in Discord server
- Ensure DISCORD_GUILD_ID and DISCORD_CHANNEL_ID are correct

### Getting Logs

**View specific service logs:**
1. Container Manager → Containers
2. Click on container name
3. **Details** → **Log**

**Export logs:**
1. Container Manager → Container
2. **Action** → **Export**

### Performance Monitoring

**Resource Usage:**
1. Container Manager → Containers
2. View CPU and Memory usage
3. Adjust if needed in **Resource Limit**

**System Resources:**
1. DSM **Resource Monitor**
2. Check overall NAS performance

## 🔒 Security Considerations

### Network Security
- Change default admin passwords
- Enable 2FA on Synology account
- Use strong passwords in `.env`
- Consider VPN for external access

### Container Security
- All services run as non-root users
- Network isolation between containers
- No sensitive data in container images

### Data Protection
- Regular backups of `/docker/rarsms/` folder
- Monitor system logs for security events
- Keep DSM and Container Manager updated

## 🎯 Synology Best Practices

### Resource Allocation
```yaml
# Add to services in docker-compose.yml if needed
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

### Storage Optimization
- Use SSD cache if available
- Place data on fastest volume
- Enable compression for backups

### Monitoring
- Set up DSM notifications for container issues
- Monitor disk space usage
- Configure email alerts for system issues

## 📱 Remote Management

### Mobile Access
- Synology **DS cloud** app
- **Container Manager** mobile interface
- VPN for secure remote access

### External Access
- Configure DDNS for remote access
- Use Synology QuickConnect
- Set up SSL certificates for HTTPS

## ✅ Post-Installation Checklist

- [ ] All containers running and healthy
- [ ] Web dashboard accessible
- [ ] APRS connector shows online status
- [ ] Discord bot responds to commands
- [ ] Email notifications working
- [ ] Backup scheduled
- [ ] Firewall configured
- [ ] DDNS setup (if needed)
- [ ] Admin account configured
- [ ] Test message routing end-to-end

## 🎉 Success!

Your RARSMS system is now running 24/7 on your Synology NAS!

**Access Points:**
- 🌐 **Dashboard**: `http://your-nas-ip:8090`
- 📊 **Admin**: `http://your-nas-ip:8090/_/`
- 🐳 **Container Manager**: DSM → Container Manager

**Next Steps:**
1. Create admin account in web dashboard
2. Approve member registrations
3. Test APRS to Discord messaging
4. Configure backups and monitoring

Your amateur radio club now has a professional, reliable messaging bridge running on your home network! 📡