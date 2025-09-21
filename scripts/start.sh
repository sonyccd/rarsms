#!/bin/bash

# RARSMS Start Script
# Starts all RARSMS services using Docker Compose

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

echo "🚀 Starting RARSMS"
echo "=================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: Please run this script from the RARSMS project root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please run ./scripts/setup.sh first"
    exit 1
fi

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

print_step "Starting RARSMS services"

# Start services
$COMPOSE_CMD up -d

print_step "Waiting for services to be ready"

# Wait for PocketBase to be ready
print_status "Waiting for PocketBase to start..."
timeout=60
counter=0

while [ $counter -lt $timeout ]; do
    if curl -s http://localhost:8090/api/health &> /dev/null; then
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

echo ""

if [ $counter -ge $timeout ]; then
    print_warning "PocketBase health check timed out, but continuing..."
else
    print_status "PocketBase is ready"
fi

print_step "Service status"

# Show service status
$COMPOSE_CMD ps

print_step "RARSMS is now running!"

echo ""
print_status "Access points:"
echo "  🌐 Web Dashboard: http://localhost:8090"
echo "  📊 Admin Panel: http://localhost:8090/_/"
echo ""
print_status "Useful commands:"
echo "  📋 View logs: ./scripts/logs.sh"
echo "  🔄 Restart: ./scripts/restart.sh"
echo "  ⏹️  Stop: ./scripts/stop.sh"
echo "  📈 Status: ./scripts/status.sh"
echo ""
print_status "Monitor logs with: docker-compose logs -f"