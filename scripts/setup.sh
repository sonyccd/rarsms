#!/bin/bash

# RARSMS Setup Script
# This script helps set up the RARSMS system for first-time deployment

set -e

echo "🚀 RARSMS Setup Script"
echo "======================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}==>${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the RARSMS project root directory"
    exit 1
fi

print_step "Checking prerequisites"

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

print_status "Docker and Docker Compose are available"

print_step "Setting up environment configuration"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_status "Creating .env file from example"
    cp .env.example .env
    print_warning "Please edit the .env file with your actual configuration values"
    print_warning "Required values: APRS_PASSCODE, DISCORD_TOKEN, DISCORD_GUILD_ID, DISCORD_CHANNEL_ID"
else
    print_status ".env file already exists"
fi

# Check if config.yaml exists
if [ ! -f "config/config.yaml" ]; then
    print_status "Creating config.yaml from example"
    cp config/config.example.yaml config/config.yaml
    print_warning "Please edit config/config.yaml if you need custom settings"
else
    print_status "config.yaml already exists"
fi

print_step "Creating data directories"

# Create data directories
mkdir -p data/pocketbase
print_status "Created data directories"

print_step "Building Docker images"

# Build images
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

$COMPOSE_CMD build

print_step "Validating configuration"

# Check if required environment variables are set
ENV_FILE=".env"
MISSING_VARS=()

check_env_var() {
    local var_name=$1
    if ! grep -q "^${var_name}=.\+" "$ENV_FILE" 2>/dev/null; then
        MISSING_VARS+=("$var_name")
    fi
}

check_env_var "APRS_PASSCODE"
check_env_var "DISCORD_TOKEN"
check_env_var "DISCORD_GUILD_ID"
check_env_var "DISCORD_CHANNEL_ID"

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    print_error "Missing required environment variables in .env file:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    print_warning "Please edit .env file and set these values before starting the system"
    echo ""
    echo "To get these values:"
    echo "  • APRS_PASSCODE: Calculate from your callsign at https://apps.magicbug.co.uk/passcode/"
    echo "  • DISCORD_TOKEN: Create a bot at https://discord.com/developers/applications"
    echo "  • DISCORD_GUILD_ID: Right-click your Discord server → Copy Server ID"
    echo "  • DISCORD_CHANNEL_ID: Right-click the target channel → Copy Channel ID"
    echo ""
    exit 1
fi

print_step "Setup complete!"

echo ""
print_status "Next steps:"
echo "1. Review and edit .env file with your actual values"
echo "2. Review config/config.yaml for any custom settings"
echo "3. Start the system with: ./scripts/start.sh"
echo ""
print_status "To start the system now: ./scripts/start.sh"
print_status "To view logs: ./scripts/logs.sh"
print_status "To stop the system: ./scripts/stop.sh"

echo ""
echo "📡 RARSMS setup is ready!"
echo "Visit http://localhost:8090 after starting to access the web dashboard"