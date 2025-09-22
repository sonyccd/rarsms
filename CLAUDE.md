# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RARSMS (Raleigh Amateur Radio Society Messaging Service) is a containerized APRS-to-Discord bridge that connects to APRS-IS, filters packets from authorized callsigns, and forwards them to Discord via webhook. The system is designed for 24/7 amateur radio operations with automatic reconnection and graceful error handling.

## Architecture

The application is a single-container Python service with the following key components:

- **RARSMSBridge Class** (`main.py`): Main application class that handles the entire APRS-to-Discord pipeline
- **APRS-IS Connection**: Telnet-based connection to amateur radio packet network with geographic filtering
- **Packet Parser**: Handles APRS position (`!`, `=`, `@`) and message (`:`) packet formats
- **Discord Integration**: Webhook-based Discord messaging with rich embeds
- **Configuration System**: Hybrid environment variable + YAML file configuration with precedence rules

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

## Development Commands

### Container Operations
```bash
# Build and run the bridge
docker-compose up -d --build

# View real-time logs
docker-compose logs -f rarsms

# Stop the service
docker-compose down

# Restart after changes
docker-compose restart rarsms
```

### Configuration Setup
```bash
# Create environment file from template
cp .env.example .env

# Edit with actual credentials (required)
# - APRS_CALLSIGN: Your amateur radio callsign
# - APRS_PASSCODE: Calculate at https://apps.magicbug.co.uk/passcode/
# - DISCORD_WEBHOOK_URL: Discord channel webhook URL
```

### Local Development
```bash
# Run Python directly (requires .env file)
python main.py

# Manual Docker build
docker build -t rarsms .
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

This is an amateur radio club project for message aggregation across multiple networks. The current implementation focuses on APRS-to-Discord bridging as Phase 1, with planned expansion to include TARPN Network, Winlink, and other amateur radio services.