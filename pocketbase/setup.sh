#!/bin/sh
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POCKETBASE_DIR="/pb"
DATA_DIR="/pb/pb_data"
COLLECTIONS_FILE="/pb/pocketbase_collections.json"
DB_FILE="${DATA_DIR}/data.db"

echo -e "${BLUE}🚀 RARSMS PocketBase Setup Starting...${NC}"

# Function to generate random password
generate_password() {
    cat /dev/urandom | tr -dc 'a-zA-Z0-9!@#$%^&*' | fold -w 16 | head -n 1
}

# Function to wait for PocketBase to be ready
wait_for_pocketbase() {
    echo -e "${YELLOW}⏳ Waiting for PocketBase to be ready...${NC}"
    for i in $(seq 1 30); do
        if wget --no-verbose --tries=1 --spider http://localhost:8090/api/health 2>/dev/null; then
            echo -e "${GREEN}✅ PocketBase is ready!${NC}"
            return 0
        fi
        echo "   Attempt $i/30..."
        sleep 2
    done
    echo -e "${RED}❌ PocketBase failed to start within 60 seconds${NC}"
    exit 1
}

# Function to create admin user
create_admin() {
    local email="admin@rarsms.local"
    ADMIN_PASSWORD=$(generate_password)  # Store in global variable

    echo -e "${BLUE}👤 Creating super admin user...${NC}"

    # Kill the background PocketBase process temporarily to run superuser command
    kill $PB_PID 2>/dev/null || true
    sleep 2

    # Create admin using PocketBase CLI command
    ./pocketbase superuser upsert "$email" "$ADMIN_PASSWORD" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Super admin user created successfully!${NC}"
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo -e "${GREEN}🔐 ADMIN CREDENTIALS (SAVE THESE!)${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Email:    ${email}${NC}"
        echo -e "${YELLOW}Password: ${ADMIN_PASSWORD}${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════${NC}"
        echo ""
        echo -e "${BLUE}💡 Access admin panel at: http://localhost:8090/_/${NC}"
        echo ""

        # Restart PocketBase in background
        ./pocketbase serve --http=0.0.0.0:8090 &
        PB_PID=$!
        sleep 3  # Wait for restart

        return 0
    else
        echo -e "${RED}❌ Failed to create admin user${NC}"
        # Restart PocketBase anyway
        ./pocketbase serve --http=0.0.0.0:8090 &
        PB_PID=$!
        sleep 3
        return 1
    fi
}

# Function to authenticate and get admin token
get_admin_token() {
    local email="admin@rarsms.local"

    echo -e "${BLUE}🔑 Getting admin authentication token...${NC}"

    local response=$(curl -s -X POST http://localhost:8090/api/collections/_superusers/auth-with-password \
        -H "Content-Type: application/json" \
        -d "{
            \"identity\": \"${email}\",
            \"password\": \"${ADMIN_PASSWORD}\"
        }")

    if echo "$response" | grep -q '"token"'; then
        echo "$response" | grep -o '"token":"[^"]*' | cut -d'"' -f4
    else
        echo -e "${RED}❌ Failed to authenticate admin${NC}"
        echo "Response: $response"
        return 1
    fi
}

# Function to import collections
import_collections() {
    local token="$1"

    if [ ! -f "$COLLECTIONS_FILE" ]; then
        echo -e "${RED}❌ Collections file not found: $COLLECTIONS_FILE${NC}"
        return 1
    fi

    echo -e "${BLUE}📦 Importing collection schemas...${NC}"

    local response=$(curl -s -X PUT http://localhost:8090/api/collections/import \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "{\"collections\": $(cat "$COLLECTIONS_FILE"), \"deleteMissing\": false}")

    if echo "$response" | grep -q '"collections"'; then
        echo -e "${GREEN}✅ Collections imported successfully!${NC}"

        # List imported collections
        echo -e "${BLUE}📋 Imported collections:${NC}"
        echo "$response" | grep -o '"name":"[^"]*' | cut -d'"' -f4 | sed 's/^/   - /'
        return 0
    else
        echo -e "${RED}❌ Failed to import collections${NC}"
        echo "Response: $response"
        return 1
    fi
}

# Main setup function
main() {
    # Check if this is a new installation
    if [ -f "$DB_FILE" ]; then
        echo -e "${YELLOW}📁 Existing PocketBase database found - skipping setup${NC}"
        echo -e "${BLUE}🚀 Starting PocketBase server...${NC}"
        exec ./pocketbase serve --http=0.0.0.0:8090
        return 0
    fi

    echo -e "${GREEN}🆕 New installation detected - running automated setup${NC}"

    # Start PocketBase in background
    echo -e "${BLUE}🚀 Starting PocketBase server...${NC}"
    ./pocketbase serve --http=0.0.0.0:8090 &
    PB_PID=$!

    # Wait for PocketBase to be ready
    wait_for_pocketbase

    # Create admin user
    if ! create_admin; then
        kill $PB_PID 2>/dev/null || true
        exit 1
    fi

    # Wait for admin user to be fully created
    echo -e "${BLUE}⏳ Waiting 5 seconds for admin user to be fully created...${NC}"
    sleep 5

    # Get admin token
    local admin_token=$(get_admin_token)
    if [ -z "$admin_token" ]; then
        echo -e "${RED}❌ Could not get admin token - collections import skipped${NC}"
        echo -e "${BLUE}💡 You can manually import collections via admin panel${NC}"
        echo -e "${BLUE}💡 Collections file location: /pb/pocketbase_collections.json${NC}"
    else
        # Import collections
        if import_collections "$admin_token"; then
            echo -e "${GREEN}✅ Collections imported successfully!${NC}"
        else
            echo -e "${YELLOW}⚠️  Collection import failed - you can import manually${NC}"
            echo -e "${BLUE}💡 Collections file location: /pb/pocketbase_collections.json${NC}"
        fi
    fi

    echo -e "${GREEN}🎉 RARSMS PocketBase setup completed!${NC}"
    echo -e "${BLUE}📍 PocketBase is running and ready to use${NC}"

    # Keep PocketBase running in foreground
    wait $PB_PID
}

# Run main function
main "$@"