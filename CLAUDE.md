# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RARSMS (Raleigh Amateur Radio Society Messaging Service) is a complete messaging aggregator and router that bridges APRS, Discord, and other amateur radio communication platforms. The system enables seamless communication across multiple networks through a hub-and-spoke architecture.

## Current Architecture

**Phase 1 Complete**: Full APRS-Discord bridge implementation
- **PocketBase**: Database, authentication, and web dashboard
- **APRS Connector** (Go): Handles APRS-IS connection and message parsing
- **Discord Bot** (Python): Manages Discord integration and threading
- **Web Dashboard**: Member portal and admin interface

## Project Status

**Development Phase:** Phase 1 implemented and ready for deployment
- ✅ Complete APRS-Discord bidirectional messaging
- ✅ Member authentication with approval workflow
- ✅ Email notifications for user management
- ✅ Docker-based deployment
- ✅ Web dashboard for message history
- ⏳ Future: TARPN Network and Winlink integration

## Technical Stack

**Current Implementation**:
- **Database**: PocketBase (SQLite-based with REST API)
- **APRS Service**: Go with telnet APRS-IS connection
- **Discord Service**: Python with discord.py
- **Frontend**: HTML/JS with PocketBase auth
- **Deployment**: Docker Compose with health checks
- **Email**: SMTP integration for approval workflow

## Development Commands

### Build and Deployment
```bash
# Setup and configuration
./scripts/setup.sh              # Initial setup and configuration check
./scripts/start.sh               # Start all services
./scripts/stop.sh                # Stop all services
./scripts/restart.sh [service]   # Restart services

# Monitoring and debugging
./scripts/status.sh              # Check service status and health
./scripts/logs.sh [-f] [service] # View logs (follow mode, specific service)

# Docker commands
docker-compose build             # Build all images
docker-compose up -d             # Start in background
docker-compose ps                # Show running containers
```

### Service Management
- **PocketBase**: http://localhost:8090 (web dashboard)
- **Admin Panel**: http://localhost:8090/_/ (database administration)
- **Services**: `pocketbase`, `aprs-connector`, `discord-bot`

## Code Organization

### Directory Structure
```
rarsms/
├── services/
│   ├── aprs-connector/          # Go APRS service
│   │   ├── src/                 # Go source code
│   │   ├── go.mod               # Go dependencies
│   │   └── Dockerfile           # Container build
│   ├── discord-bot/             # Python Discord service
│   │   ├── src/                 # Python source code
│   │   ├── requirements.txt     # Python dependencies
│   │   └── Dockerfile           # Container build
│   └── web-dashboard/           # PocketBase + web UI
│       ├── pb_hooks/            # PocketBase JavaScript hooks
│       ├── pb_migrations/       # Database migrations
│       ├── pb_public/           # Web interface files
│       └── Dockerfile           # Container build
├── config/                      # Configuration files
├── scripts/                     # Management scripts
├── data/                        # Persistent data (created at runtime)
└── docker-compose.yml           # Service orchestration
```

### Database Schema
- `users` - Authentication with approval workflow
- `member_profiles` - Member callsigns and details
- `messages` - All routed messages with correlation
- `conversations` - Grouped message threads
- `system_logs` - Event logging and audit trail
- `aprs_packets` - Raw APRS packet storage
- `discord_threads` - Discord thread tracking
- `system_status` - Service health monitoring
- `pending_approvals` - User approval workflow

## Configuration

### Environment Variables (.env)
Key configuration values:
- `APRS_CALLSIGN`, `APRS_PASSCODE` - APRS-IS credentials
- `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_CHANNEL_ID` - Discord integration
- `SMTP_USERNAME`, `SMTP_PASSWORD` - Email notifications
- `LOG_LEVEL`, `LOG_FORMAT` - Logging configuration

### Config Files
- `config/config.yaml` - Main application configuration
- `config/config.example.yaml` - Configuration template
- `config/members.json` - Initial member data (for reference)

## Key Features

### Authentication & Security
- Callsign-based user registration
- Admin approval workflow with email notifications
- Member-only message access (privacy-first)
- Account self-deletion with complete data removal

### Message Routing
- APRS messages to "RARSMS" callsign appear in Discord
- Discord thread replies route back to APRS stations
- Correlation IDs track conversations across platforms
- Message status tracking (pending/delivered/failed)

### System Monitoring
- Service health checks and status reporting
- Comprehensive logging with structured format
- Web dashboard for message history
- Admin panel for user and system management

## Development Notes

- **Target Callsign**: `RARSMS` (configurable)
- **Message Correlation**: Each conversation has unique correlation ID
- **Error Handling**: Automatic reconnection for all network connections
- **Compliance**: FCC Part 97 compliant for amateur radio operations
- **Scalability**: Designed for easy addition of new messaging services (TARPN, Winlink)

## Testing and Validation

### Service Health Checks
- PocketBase: HTTP health endpoint
- APRS Connector: Connection status monitoring
- Discord Bot: Heartbeat and latency monitoring

### Log Monitoring
```bash
./scripts/logs.sh -f aprs        # Follow APRS connector logs
./scripts/logs.sh -f discord     # Follow Discord bot logs
./scripts/logs.sh -f pocketbase  # Follow database logs
```

## Deployment Considerations

- **Production**: Set strong passwords, configure proper SMTP, use environment secrets
- **Development**: Use debug logging, email dev mode, local configuration
- **Security**: All services run as non-root users, network isolation
- **Persistence**: Database and configuration mounted as volumes
- **Monitoring**: Health checks and restart policies configured