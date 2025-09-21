#!/bin/bash

# RARSMS Logs Script
# View logs from RARSMS services

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

# Parse command line arguments
SERVICE=""
FOLLOW=false
TAIL_LINES=100

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -n|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        pocketbase|aprs|discord|aprs-connector|discord-bot)
            SERVICE="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [SERVICE]"
            echo ""
            echo "Services:"
            echo "  pocketbase     - PocketBase database and web dashboard"
            echo "  aprs-connector - APRS connector service"
            echo "  discord-bot    - Discord bot service"
            echo ""
            echo "Options:"
            echo "  -f, --follow   - Follow log output (like tail -f)"
            echo "  -n, --tail N   - Show last N lines (default: 100)"
            echo "  -h, --help     - Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                    # Show all logs"
            echo "  $0 -f                 # Follow all logs"
            echo "  $0 aprs-connector     # Show APRS connector logs"
            echo "  $0 -f discord-bot     # Follow Discord bot logs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "📋 RARSMS Logs"
echo "=============="

# Build command
CMD="$COMPOSE_CMD logs"

if [ "$FOLLOW" = true ]; then
    CMD="$CMD -f"
fi

CMD="$CMD --tail=$TAIL_LINES"

if [ -n "$SERVICE" ]; then
    # Map service names to container names
    case $SERVICE in
        pocketbase)
            SERVICE="pocketbase"
            ;;
        aprs|aprs-connector)
            SERVICE="aprs-connector"
            ;;
        discord|discord-bot)
            SERVICE="discord-bot"
            ;;
    esac
    CMD="$CMD $SERVICE"
    print_status "Showing logs for: $SERVICE"
else
    print_status "Showing logs for all services"
fi

if [ "$FOLLOW" = true ]; then
    print_status "Following logs (Press Ctrl+C to stop)"
else
    print_status "Showing last $TAIL_LINES lines"
fi

echo ""

# Execute command
exec $CMD