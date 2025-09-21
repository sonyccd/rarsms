#!/bin/bash

# RARSMS Restart Script
# Restart RARSMS services

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

echo "🔄 Restarting RARSMS"
echo "==================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: Please run this script from the RARSMS project root directory"
    exit 1
fi

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Parse command line arguments for specific service restart
SERVICE=""
if [ $# -eq 1 ]; then
    case $1 in
        pocketbase|aprs-connector|discord-bot)
            SERVICE="$1"
            ;;
        aprs)
            SERVICE="aprs-connector"
            ;;
        discord)
            SERVICE="discord-bot"
            ;;
        *)
            echo "Unknown service: $1"
            echo "Available services: pocketbase, aprs-connector, discord-bot"
            exit 1
            ;;
    esac
fi

if [ -n "$SERVICE" ]; then
    print_step "Restarting $SERVICE service"
    $COMPOSE_CMD restart "$SERVICE"
    print_status "$SERVICE service restarted"
else
    print_step "Restarting all RARSMS services"
    $COMPOSE_CMD restart
    print_status "All services restarted"
fi

print_step "Service status"
$COMPOSE_CMD ps

echo ""
print_status "RARSMS restart complete"