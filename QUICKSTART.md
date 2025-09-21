# RARSMS Quick Start

Get RARSMS running in 5 minutes!

## 🚀 Super Quick Start

```bash
# 1. Clone
git clone <repository-url>
cd rarsms

# 2. Fix Docker permissions (if needed)
sudo usermod -aG docker $USER
# Log out and back in, then:

# 3. Setup
docker compose --profile setup run --rm setup

# 4. Configure (edit these values!)
nano .env

# 5. Start
docker compose up -d

# 6. Access
open http://localhost:8090
```

## ⚡ Required Configuration

Edit `.env` with these **required** values:

```bash
# Get APRS passcode: https://apps.magicbug.co.uk/passcode/
APRS_CALLSIGN=RARSMS
APRS_PASSCODE=12345

# Create Discord bot: https://discord.com/developers/applications
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id
DISCORD_CHANNEL_ID=your_channel_id

# Email for user approvals
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin@yourclub.org
```

## 🎯 First Steps After Setup

1. **Access Dashboard**: http://localhost:8090
2. **Create Admin Account**: Register → Login to admin panel at http://localhost:8090/_/
3. **Test APRS**: Send message to "RARSMS" callsign
4. **Check Discord**: Message should appear in your Discord channel
5. **Reply Test**: Reply in Discord thread → should go back to APRS

## 📱 Platform-Specific Quick Start

### Synology NAS
1. Install Container Manager package
2. Upload RARSMS files via File Station
3. Use Container Manager to create project
4. Edit .env via File Station
5. Deploy via Container Manager interface

### Linux Server
```bash
# Install Docker first
sudo apt install docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# Logout/login, then follow main quick start
```

### Windows/macOS
1. Install Docker Desktop
2. Follow main quick start steps
3. No permission issues with Docker Desktop

## 🔧 Quick Commands

```bash
# Status check
docker compose ps

# View logs
docker compose logs

# Stop/start
docker compose down
docker compose up -d

# Update
git pull
docker compose build
docker compose up -d
```

## 🚨 Quick Troubleshooting

**Permission denied?**
```bash
sudo usermod -aG docker $USER
# Logout and login
```

**Port 8090 in use?**
```yaml
# Edit docker-compose.yml
ports:
  - "8091:8090"
```

**Services not starting?**
```bash
docker compose logs
# Check .env has all required values
```

**Can't connect to APRS?**
- Verify APRS_PASSCODE is correct
- Check internet connectivity

**Discord bot offline?**
- Verify DISCORD_TOKEN
- Check bot permissions in Discord server

## ✅ Success Indicators

- ✅ All containers showing "running" or "healthy"
- ✅ Web dashboard loads at http://localhost:8090
- ✅ Can create account and login
- ✅ APRS connector shows "online" in dashboard
- ✅ Discord bot responds to `!status` command
- ✅ Test message routes APRS → Discord → APRS

## 📚 Next Steps

- **Add Members**: Share registration link with club members
- **Configure Backup**: Setup regular backups of data/ directory
- **Production Setup**: Configure SSL, firewall, monitoring
- **Read Full Docs**: README.md for complete documentation

**Need Help?**
- Docker issues: README-DOCKER-PERMISSIONS.md
- Synology NAS: README-SYNOLOGY.md
- Full deployment: README-DOCKER-ONLY.md

Happy messaging! 📡 73!