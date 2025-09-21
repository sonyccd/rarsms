# RARSMS - Docker Compose Management
# Use 'make' commands instead of bash scripts for better portability

.PHONY: help setup start stop restart status logs clean build

# Default target
help:
	@echo "🚀 RARSMS - Raleigh Amateur Radio Society Messaging Service"
	@echo "============================================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup    - Initial setup and configuration check"
	@echo "  make start    - Start all services"
	@echo "  make stop     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make status   - Show service status"
	@echo "  make logs     - Show logs from all services"
	@echo "  make build    - Build all Docker images"
	@echo "  make clean    - Stop and remove all containers and volumes"
	@echo ""
	@echo "Service-specific logs:"
	@echo "  make logs-aprs     - Show APRS connector logs"
	@echo "  make logs-discord  - Show Discord bot logs"
	@echo "  make logs-db       - Show PocketBase logs"
	@echo ""
	@echo "Configuration:"
	@echo "  Copy .env.example to .env and configure your values"
	@echo "  Edit config/config.yaml if needed"
	@echo ""
	@echo "Access points after starting:"
	@echo "  🌐 Web Dashboard: http://localhost:8090"
	@echo "  📊 Admin Panel: http://localhost:8090/_/"

# Check if required files exist and create them if needed
setup:
	@echo "🚀 RARSMS Setup"
	@echo "==============="
	@echo ""
	@echo "📋 Checking configuration files..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from example..."; \
		cp .env.example .env; \
		echo "⚠️  Please edit .env with your actual configuration values"; \
		echo "   Required: APRS_PASSCODE, DISCORD_TOKEN, DISCORD_GUILD_ID, DISCORD_CHANNEL_ID"; \
	else \
		echo "✅ .env file exists"; \
	fi
	@if [ ! -f config/config.yaml ]; then \
		echo "Creating config.yaml from example..."; \
		cp config/config.example.yaml config/config.yaml; \
		echo "✅ config.yaml created"; \
	else \
		echo "✅ config.yaml exists"; \
	fi
	@echo ""
	@echo "📁 Creating data directories..."
	@mkdir -p data/pocketbase
	@echo "✅ Data directories created"
	@echo ""
	@echo "🔧 Validating configuration..."
	@if ! grep -q "^APRS_PASSCODE=.\+" .env 2>/dev/null; then \
		echo "❌ APRS_PASSCODE not set in .env"; \
		echo "   Calculate from your callsign at: https://apps.magicbug.co.uk/passcode/"; \
		exit 1; \
	fi
	@if ! grep -q "^DISCORD_TOKEN=.\+" .env 2>/dev/null; then \
		echo "❌ DISCORD_TOKEN not set in .env"; \
		echo "   Create a bot at: https://discord.com/developers/applications"; \
		exit 1; \
	fi
	@if ! grep -q "^DISCORD_GUILD_ID=.\+" .env 2>/dev/null; then \
		echo "❌ DISCORD_GUILD_ID not set in .env"; \
		echo "   Right-click your Discord server → Copy Server ID"; \
		exit 1; \
	fi
	@if ! grep -q "^DISCORD_CHANNEL_ID=.\+" .env 2>/dev/null; then \
		echo "❌ DISCORD_CHANNEL_ID not set in .env"; \
		echo "   Right-click the target channel → Copy Channel ID"; \
		exit 1; \
	fi
	@echo "✅ Configuration validation passed"
	@echo ""
	@echo "🎉 Setup complete!"
	@echo "Next: Run 'make start' to launch RARSMS"

# Build all Docker images
build:
	@echo "🔨 Building Docker images..."
	docker compose build

# Start all services
start: setup build
	@echo "🚀 Starting RARSMS services..."
	docker compose up -d
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo ""
	@echo "✅ RARSMS is now running!"
	@echo ""
	@echo "📊 Service Status:"
	@docker compose ps
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  Web Dashboard: http://localhost:8090"
	@echo "  Admin Panel: http://localhost:8090/_/"
	@echo ""
	@echo "📋 Useful Commands:"
	@echo "  make status - Check service status"
	@echo "  make logs   - View all logs"
	@echo "  make stop   - Stop all services"

# Stop all services
stop:
	@echo "⏹️  Stopping RARSMS services..."
	docker compose down
	@echo "✅ All services stopped"

# Restart all services
restart:
	@echo "🔄 Restarting RARSMS services..."
	docker compose restart
	@echo "✅ All services restarted"

# Show service status
status:
	@echo "📊 RARSMS Service Status"
	@echo "========================"
	@echo ""
	@echo "🐳 Container Status:"
	@docker compose ps
	@echo ""
	@echo "🔍 Health Checks:"
	@printf "🗄️  PocketBase: "
	@if curl -s http://localhost:8090/api/health >/dev/null 2>&1; then \
		echo "✅ Healthy"; \
	else \
		echo "❌ Unhealthy"; \
	fi
	@echo ""
	@echo "📈 Resource Usage:"
	@docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $$(docker compose ps -q) 2>/dev/null || echo "Resource info not available"

# Show logs from all services
logs:
	@echo "📋 RARSMS Logs (last 50 lines)"
	@echo "==============================="
	docker compose logs --tail=50

# Follow logs from all services
logs-follow:
	@echo "📋 Following RARSMS Logs (Press Ctrl+C to stop)"
	@echo "================================================"
	docker compose logs -f

# Service-specific logs
logs-aprs:
	@echo "📡 APRS Connector Logs"
	@echo "======================"
	docker compose logs --tail=100 aprs-connector

logs-discord:
	@echo "🤖 Discord Bot Logs"
	@echo "==================="
	docker compose logs --tail=100 discord-bot

logs-db:
	@echo "🗄️  PocketBase Logs"
	@echo "==================="
	docker compose logs --tail=100 pocketbase

# Clean up everything (destructive!)
clean:
	@echo "🧹 Cleaning up RARSMS (this will remove all data!)"
	@echo "Are you sure? This will delete all messages and user data."
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read
	docker compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

# Development helpers
dev:
	@echo "🔧 Starting RARSMS in development mode..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Check configuration without starting
check-config:
	@echo "🔍 Checking Docker Compose configuration..."
	docker compose config

# Pull latest images
pull:
	@echo "📥 Pulling latest base images..."
	docker compose pull