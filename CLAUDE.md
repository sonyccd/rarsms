# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RARSMS (Raleigh Amateur Radio Society Messaging Service) is a containerized APRS-to-Discord bridge that connects to APRS-IS, filters packets from authorized callsigns, and forwards them to Discord via webhook. The system is designed for 24/7 amateur radio operations with automatic reconnection and graceful error handling.

## Architecture

The application is a multi-container system with the following key components:

### Core Services
- **RARSMSBridge Class** (`main.py`): Main application class that handles the entire APRS-to-Discord pipeline
- **APRS-IS Connection**: Telnet-based connection to amateur radio packet network with geographic filtering
- **Packet Parser**: Handles APRS position (`!`, `=`, `@`) and message (`:`) packet formats
- **Discord Integration**: Webhook-based Discord messaging with rich embeds
- **Configuration System**: Hybrid environment variable + YAML file configuration with precedence rules

### Data & Interface Layer
- **PocketBase Database** (v0.30): Real-time database with WebSocket support for live updates
- **Live APRS Viewer**: Web interface displaying real-time APRS packets with geographic data
- **Management Interface**: Role-based admin panel for callsign and configuration management
- **User Authentication**: Role-based access control (admin/user roles)
- **Configuration Management**: Web-based forms for APRS, Discord, filtering, and database settings
- **Statistics Dashboard**: Real-time message analytics with protocol breakdown
- **Search Interface**: Full-text search across all messages with filtering
- **Persistent Storage**: Docker volumes for database and static files

### Configuration Hierarchy

The application loads configuration in this order (later sources override earlier ones):
1. Default values in code
2. `config.yaml` file (optional)
3. Environment variables (highest precedence)

Required environment variables: `APRS_CALLSIGN`, `APRS_PASSCODE`, `DISCORD_WEBHOOK_URL`

### Callsign Authorization

The system filters APRS packets by callsign using two sources:
- `callsigns.txt`: One base callsign per line (ignores SSIDs)
- `AUTHORIZED_CALLSIGNS` environment variable: Comma-separated list

## Quick Start (Zero Configuration)

### Automated Setup
```bash
# Complete setup with zero configuration required
docker compose up --build

# Watch logs for generated admin credentials
docker compose logs -f pocketbase
```

**That's it!** The system automatically:
- ✅ Creates PocketBase superuser with random password
- ✅ Displays admin credentials in logs (save these!)
- ✅ Sets up all database collections
- ✅ Starts live APRS viewer with role-based authentication

### Access Points
- **Live APRS Viewer**: http://localhost:8090/ (public access)
  - Real-time message feed with WebSocket updates
  - Statistics dashboard with protocol breakdown
  - Message search with full-text filtering
  - Admin authentication for management features
- **Admin Panel**: http://localhost:8090/_/ (use generated credentials)
  - Direct PocketBase database administration
  - User management and role assignment
  - Collection schema management
- **Management Interface**: Integrated into live viewer (admin login required)
  - Callsign management (add/remove/toggle authorized callsigns)
  - System configuration (APRS, Discord, filtering settings)
  - Real-time statistics and analytics
- **Test Suite**: http://localhost:8090/test.html (admin access via 🧪 Tests link)
  - Frontend unit tests with visual results
  - Authentication, configuration, and validation testing

## Development Commands

### Container Operations
```bash
# Build and run the complete system
docker compose up -d --build

# View setup logs and find admin credentials
docker compose logs pocketbase

# View APRS bridge logs
docker compose logs rarsms

# Stop all services (preserves data in volumes)
docker compose down

# Complete reset (WARNING: deletes all data including host files)
docker compose down -v && rm -rf ./pocketbase/pb_data/*

# Or use the helper script
./reset.sh

# Restart after changes
docker compose restart

# View volume information
docker volume ls
docker volume inspect rarsms_pocketbase_data
```

### Configuration Setup (Advanced)
```bash
# Create environment file for custom configuration
cp .env.example .env

# Edit with actual credentials (optional - for APRS/Discord integration)
# - APRS_CALLSIGN: Your amateur radio callsign
# - APRS_PASSCODE: Calculate at https://apps.magicbug.co.uk/passcode/
# - DISCORD_WEBHOOK_URL: Discord channel webhook URL
```

### Testing Commands
```bash
# Frontend tests (visual results in browser)
open http://localhost:8090/test.html

# Backend tests (Python pytest suite)
python3 run_tests.py

# Run specific backend test category
python3 run_tests.py aprs

# Run tests with coverage reporting
python3 run_tests.py --coverage

# Validate complete test infrastructure
./validate_tests.sh

# PocketBase integration tests
./test_pocketbase.sh
```

### Local Development
```bash
# Run Python directly (requires .env file)
python main.py

# Manual Docker build
docker build -t rarsms .
```

### Automated Setup Details

The PocketBase container includes an automated setup script (`pocketbase/setup.sh`) that:

1. **Detects New Installation**: Checks if `pb_data/data.db` exists
2. **Creates Super Admin**: Uses `pocketbase superuser` command with generated credentials
3. **Displays Credentials**: Shows admin email/password in colored, prominent format in logs
4. **Graceful Operation**: Continues successfully even if optional collection import is not completed
5. **Manual Collection Setup**: Provides clear instructions for completing setup via admin interface

**Setup Process:**
```
🚀 RARSMS PocketBase Setup Starting...
🆕 New installation detected - running automated setup
✅ PocketBase is ready!
👤 Creating super admin user...
✅ Super admin user created successfully!

═══════════════════════════════════════════
🔐 ADMIN CREDENTIALS (SAVE THESE!)
═══════════════════════════════════════════
Email:    admin@rarsms.local
Password: [16-character random password]
═══════════════════════════════════════════

💡 Access admin panel at: http://localhost:8090/_/
```

### User Management

**Admin Users**: Can access all features including:
- Callsign management (add/remove authorized callsigns)
- Configuration management (system settings)
- Full database access via PocketBase admin panel

**Regular Users**: Limited access for future features
- Can be created through PocketBase admin panel
- Role field determines access level (`admin` or `user`)

### Post-Setup Configuration

**Complete the setup** (one-time only):
1. Access PocketBase admin panel at http://localhost:8090/_/ with generated credentials
2. **Add role field to users collection**:
   - Go to Collections → users → Settings → Fields
   - Click "+ New field" → Select type → add `role` field with options: `user`, `admin`
3. **Import additional collections** (optional):
   - Go to Settings → Import collections
   - Upload `/home/brad/Dev/rarsms/pocketbase_collections.json`

**Create additional admin users**:
1. Navigate to Collections → users → Records
2. Create new user with `role: "admin"`

### Data Persistence

RARSMS uses Docker volumes for persistent data storage:

**Volume Structure:**
```
rarsms_pocketbase_data/     # Database files, configurations, logs
  ├── data.db              # Main SQLite database
  ├── logs.db              # System logs
  └── backups/             # Automatic backups

rarsms_pocketbase_public/   # Static web files
  ├── index.html           # Live APRS viewer
  ├── app.js               # Frontend application
  └── assets/              # Static assets
```

**Volume Management:**
- **Automatic creation**: Volumes created on first `docker compose up`
- **Data persistence**: Database survives container restarts and rebuilds
- **Backup location**: `./pocketbase/pb_data/` (bound to host filesystem)
- **Web files**: `./pocketbase/pb_public/` (bound to host filesystem)

**Data Safety:**
```bash
# Safe restart (preserves all data)
docker compose restart

# Safe rebuild (preserves all data)
docker compose down && docker compose up --build

# DANGER: Complete reset (deletes all data)
docker compose down -v && rm -rf ./pocketbase/pb_data/*

# Or use the helper script (includes safety prompt)
./reset.sh

# Alternative: Reset just database (keeps web files)
rm -rf ./pocketbase/pb_data/* && docker compose restart pocketbase
```

## Key Implementation Details

### APRS-IS Login Process
The connection follows the APRS-IS protocol requiring:
1. TCP connection to `rotate.aprs2.net:14580`
2. Send login command: `user CALLSIGN pass PASSCODE vers APP filter GEOGRAPHIC_FILTER`
3. Wait for `# logresp` response containing "verified"
4. Switch to non-blocking mode for packet processing

### Geographic Filtering
Uses APRS-IS server-side filtering with format: `r/lat/lon/distance_km`
Default centered on Raleigh, NC (35.7796, -78.6382) with 100km radius.

### Discord Message Format
Sends rich embeds containing:
- Source callsign with SSID
- Geographic coordinates (for position packets)
- Message content and recipient (for message packets)
- Raw packet data for debugging
- UTC timestamp

### Error Handling and Reconnection
- Automatic reconnection on APRS-IS connection loss
- Graceful shutdown on SIGTERM/SIGINT
- Discord webhook retry logic
- Comprehensive logging to stdout for container environments

## Project Context

This is an amateur radio club project for message aggregation across multiple networks. The system includes:

**Phase 1 (Complete)**: APRS-to-Discord bridging with PocketBase integration
- ✅ Real-time APRS packet processing and forwarding
- ✅ Live web viewer with WebSocket updates
- ✅ Role-based management interface
- ✅ Automated deployment and setup

**Phase 2 (Planned)**: Multi-protocol expansion
- TARPN Network integration
- Winlink gateway support
- Additional amateur radio services
- Cross-protocol message routing

The automated setup system ensures zero-configuration deployment, making it easy for amateur radio clubs to deploy and maintain their own instances.