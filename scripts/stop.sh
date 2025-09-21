#!/bin/bash

# RARSMS Stop Script
# Stops all RARSMS services

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

echo "⏹️  Stopping RARSMS"
echo "=================="

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

print_step "Stopping RARSMS services"

# Stop services
$COMPOSE_CMD down

print_status "All RARSMS services have been stopped"

echo ""
print_status "To start again: ./scripts/start.sh"
print_status "To remove all data: ./scripts/clean.sh"