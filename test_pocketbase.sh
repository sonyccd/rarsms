#!/bin/bash

# Test PocketBase Container Setup
echo "🧪 Testing PocketBase setup..."

# Check for cleanup flag
if [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    echo "🧹 Cleaning PocketBase data..."
    docker compose down
    rm -rf pocketbase/pb_data
    mkdir -p pocketbase/pb_data
    touch pocketbase/pb_data/.gitkeep
    echo "✅ PocketBase data cleaned"
    echo ""
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ docker compose not found. Please install Docker Compose V2."
    exit 1
fi

# Validate docker compose configuration
echo "📋 Validating docker compose configuration..."
if docker compose config --quiet; then
    echo "✅ Docker compose configuration is valid"
else
    echo "❌ Docker compose configuration has errors"
    exit 1
fi

# Check directory structure
echo "📁 Checking PocketBase directory structure..."
if [ -d "pocketbase/pb_data" ] && [ -d "pocketbase/pb_public" ]; then
    echo "✅ PocketBase directories exist"
else
    echo "❌ PocketBase directories missing"
    exit 1
fi

# Test starting PocketBase
echo "🚀 Starting PocketBase container..."
if docker compose up pocketbase -d; then
    echo "✅ PocketBase container started successfully"

    echo "⏳ Waiting for PocketBase to be ready..."
    sleep 10

    # Check if PocketBase is responding
    if curl -s http://localhost:8090/api/health &> /dev/null; then
        echo "✅ PocketBase is responding on http://localhost:8090"
        echo ""
        echo "🌐 Access Points:"
        echo "   Admin Interface: http://localhost:8090/_/"
        echo "   API Base URL: http://localhost:8090/api/"
        echo "   Search Interface: http://localhost:8090/"
        echo ""

        # Extract installer token from logs if available
        echo "🔑 First-time Setup:"
        INSTALLER_URL=$(docker compose logs pocketbase 2>/dev/null | grep "pbinstal" | tail -1 | sed 's/.*http:\/\/0\.0\.0\.0:8090/http:\/\/localhost:8090/')
        if [ ! -z "$INSTALLER_URL" ]; then
            echo "   Setup URL: $INSTALLER_URL"
            echo "   Note: This URL expires after 1 hour"
        else
            echo "   Admin setup already completed or check logs manually"
        fi

        echo ""
        echo "📝 Next Steps:"
        echo "   1. Open the setup URL above to create admin account"
        echo "   2. Create 'messages' collection with the planned schema"
        echo "   3. Test the search interface at http://localhost:8090/"
    else
        echo "⚠️  PocketBase started but not responding yet. Check logs:"
        echo "   docker compose logs pocketbase"
    fi
else
    echo "❌ Failed to start PocketBase container"
    echo "Check the logs with: docker compose logs pocketbase"
    exit 1
fi

echo ""
echo "🔧 Useful Commands:"
echo "   Stop PocketBase: docker compose down"
echo "   View logs: docker compose logs -f pocketbase"
echo "   Restart: docker compose restart pocketbase"
echo "   Clean data: ./test_pocketbase.sh --clean"
echo "   Get installer URL: docker compose logs pocketbase | grep pbinstal"