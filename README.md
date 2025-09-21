# RARSMS - Raleigh Amateur Radio Society Messaging Service

A comprehensive messaging aggregator and router that bridges APRS, Discord, and other amateur radio communication platforms, enabling seamless communication across multiple networks.

## 🌟 Features

- **📡 APRS-Discord Bridge**: Real-time message routing between APRS-IS and Discord
- **👥 Member Authentication**: Secure callsign-based user management with approval workflow
- **💬 Threaded Conversations**: Discord threads automatically created for APRS conversations
- **📊 Web Dashboard**: Complete message history and system monitoring
- **🔐 Privacy-First**: Members see only their own message history
- **🐳 Docker Deployment**: One-command deployment with Docker Compose
- **📧 Email Notifications**: Automated approval workflow with email alerts
- **🔄 Auto-Reconnection**: Robust connection handling for 24/7 operation

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Amateur radio license with valid callsign
- Discord server and bot token
- SMTP access for email notifications

### Installation

**⚡ Quick Setup**
```bash
git clone <repository-url>
cd rarsms
docker compose --profile setup run --rm setup
# Edit .env with your configuration
docker compose up -d
# Set up admin account at http://localhost:8090/_/
# Create database collections (see COLLECTIONS.md)
```

**🏢 Platform-Specific Guides:**
- **Synology NAS**: `README-SYNOLOGY.md`
- **Docker-only environments**: `README-DOCKER-ONLY.md`

**🌐 Access Points:**
- **User Interface**: http://localhost:8090
- **Admin Panel**: http://localhost:8090/_/
- **API Docs**: http://localhost:8090/api/

## 📋 Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# APRS Configuration
APRS_CALLSIGN=RARSMS                    # Your station callsign
APRS_PASSCODE=12345                     # APRS-IS passcode
DISCORD_TOKEN=your_discord_bot_token    # Discord bot token
DISCORD_GUILD_ID=your_server_id         # Discord server ID
DISCORD_CHANNEL_ID=your_channel_id      # Target channel ID

# Email Configuration (for user approvals)
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAILS=admin1@club.org,admin2@club.org
```

### Getting Configuration Values

**APRS Passcode**: Calculate from your callsign at https://apps.magicbug.co.uk/passcode/

**Discord Bot Setup**:
1. Go to https://discord.com/developers/applications
2. Create a new application → Bot section
3. Copy the bot token
4. Enable "Message Content Intent"
5. Invite bot to your server with message permissions

**Discord IDs**:
1. Enable Developer Mode in Discord
2. Right-click server name → Copy Server ID
3. Right-click target channel → Copy Channel ID

## 🏗️ Architecture

RARSMS uses a hub-and-spoke architecture with PocketBase as the central message broker:

```
   APRS-IS ←→ APRS Connector ←→ PocketBase ←→ Discord Bot ←→ Discord
                                    ↕
                               Web Dashboard
```

### Components

- **PocketBase**: Database, auth, and web dashboard
- **APRS Connector** (Go): Handles APRS-IS connection and message parsing
- **Discord Bot** (Python): Manages Discord integration and threading
- **Web Dashboard**: Member portal and admin interface

## 📖 Usage

### For Club Members

1. **Register an Account**
   - Visit the web dashboard
   - Register with your callsign and email
   - Wait for admin approval

2. **Send Messages via APRS**
   - Send APRS message to callsign "RARSMS"
   - Message appears in Discord channel
   - Discord users can reply in the thread

3. **Send Messages via Discord**
   - Reply in Discord threads
   - Messages are routed back to original APRS station

### For Administrators

1. **Approve New Members**
   - Check email notifications for new registrations
   - Login to admin panel at http://localhost:8090/_/
   - Approve pending accounts

2. **Monitor System**
   - View system status in dashboard
   - Check logs: `make logs`
   - Monitor message routing

## 🛠️ Management Commands

```bash
# System Management
make start              # Start all services
make stop               # Stop all services
make restart            # Restart services
make status             # Check system status

# Logs and Monitoring
make logs               # View all logs
make logs-follow        # Follow logs in real-time
make logs-aprs          # APRS connector logs only
make logs-discord       # Discord bot logs only

# Other Commands
make help               # Show all available commands
make build              # Build Docker images
make clean              # Remove all containers (destructive)
```

## 🔧 Development

### Project Structure

```
rarsms/
├── services/
│   ├── aprs-connector/     # Go APRS service
│   ├── discord-bot/        # Python Discord service
│   └── web-dashboard/      # PocketBase + web UI
├── config/                 # Configuration files
├── scripts/               # Management scripts
└── docker-compose.yml     # Service orchestration
```

### Development Setup

1. **Development Environment**
   ```bash
   # Copy development overrides
   cp .env.example .env

   # Set development flags
   LOG_LEVEL=debug
   LOG_FORMAT=text
   EMAIL_DEV_MODE=true
   ```

2. **Build and Test**
   ```bash
   # Build all images
   docker-compose build

   # Start in development mode
   docker-compose up
   ```

### Database Schema

The system uses PocketBase with the following collections:
- `users` - Member authentication (extended with approval fields)
- `member_profiles` - Member information and callsigns
- `messages` - All routed messages with correlation
- `conversations` - Grouped message threads
- `system_logs` - Event logging and audit trail
- `aprs_packets` - Raw APRS packet storage
- `discord_threads` - Discord thread tracking

## 🔐 Security & Privacy

- **Member Authentication**: Only approved club members can use the system
- **Message Privacy**: Members see only their own message history
- **Audit Logging**: Complete system event logging
- **Data Deletion**: Users can delete their accounts and all associated data
- **Approval Workflow**: New registrations require admin approval

## 📞 Support

### Troubleshooting

**APRS not connecting**: Check callsign and passcode in `.env`
**Discord bot offline**: Verify bot token and permissions
**Email not sending**: Check SMTP credentials and Gmail app password
**Database errors**: Check PocketBase logs and data directory permissions

### Common Issues

1. **Docker Permission Denied**: Add user to docker group: `sudo usermod -aG docker $USER` (see README-DOCKER-PERMISSIONS.md)
2. **Port Conflicts**: Change port 8090 in docker-compose.yml if needed
3. **Memory Issues**: Ensure Docker has sufficient memory allocated

### Getting Help

- Check system logs: `make logs`
- View service status: `make status`
- Review configuration files in `config/` directory
- Check Discord bot permissions in your server
- See detailed deployment guide: `README-DEPLOYMENT.md`

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📡 Amateur Radio Compliance

RARSMS is designed for FCC Part 97 compliant amateur radio operations:
- Proper station identification in all automated messages
- Message logging for regulatory compliance
- Third-party traffic handling appropriate for amateur frequencies
- Emergency messaging capabilities for ARES/RACES operations

---

**73!** - The RARSMS Development Team

*Advancing the Art, Science and Enjoyment of Radio*
