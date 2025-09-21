#!/bin/bash

# RARSMS Status Script
# Show status of all RARSMS services

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

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

echo "📊 RARSMS Status"
echo "================"

print_step "Container Status"

# Show container status
$COMPOSE_CMD ps

print_step "Service Health Checks"

# Check PocketBase
echo -n "🗄️  PocketBase: "
if curl -s http://localhost:8090/api/health &> /dev/null; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Unhealthy${NC}"
fi

# Check if APRS connector is running
echo -n "📡 APRS Connector: "
APRS_STATUS=$($COMPOSE_CMD ps aprs-connector --format "table {{.State}}" | tail -n +2)
if [ "$APRS_STATUS" = "running" ]; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not Running${NC}"
fi

# Check if Discord bot is running
echo -n "🤖 Discord Bot: "
DISCORD_STATUS=$($COMPOSE_CMD ps discord-bot --format "table {{.State}}" | tail -n +2)
if [ "$DISCORD_STATUS" = "running" ]; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Not Running${NC}"
fi

print_step "Network Status"

# Check network connectivity
echo -n "🌐 Internet: "
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${GREEN}✅ Connected${NC}"
else
    echo -e "${RED}❌ No Connection${NC}"
fi

echo -n "📡 APRS-IS: "
if nc -z rotate.aprs2.net 14580 &> /dev/null 2>&1; then
    echo -e "${GREEN}✅ Reachable${NC}"
else
    echo -e "${RED}❌ Unreachable${NC}"
fi

print_step "Resource Usage"

# Show resource usage for containers
echo "Container Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose ps -q) 2>/dev/null || echo "Resource information not available"

print_step "Recent Logs (last 10 lines)"

# Show recent logs
$COMPOSE_CMD logs --tail=10

print_step "Quick Actions"

echo "📋 View all logs: ./scripts/logs.sh"
echo "🔄 Restart services: ./scripts/restart.sh"
echo "⏹️  Stop services: ./scripts/stop.sh"
echo "🌐 Web Dashboard: http://localhost:8090"