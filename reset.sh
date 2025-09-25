#!/bin/bash

# RARSMS Complete Reset Script
# This will delete ALL data and start fresh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}⚠️  WARNING: Complete RARSMS Reset${NC}"
echo -e "${RED}This will DELETE ALL data including:${NC}"
echo -e "${RED}- All PocketBase data (users, messages, configurations)${NC}"
echo -e "${RED}- Docker volumes${NC}"
echo -e "${RED}- Host filesystem data${NC}"
echo ""

read -p "Are you sure you want to continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Reset cancelled${NC}"
    exit 0
fi

echo -e "${BLUE}🛑 Stopping containers and removing volumes...${NC}"
docker compose down -v

echo -e "${BLUE}🗑️  Removing host data...${NC}"
rm -rf ./pocketbase/pb_data/*

echo -e "${GREEN}✅ Complete reset finished!${NC}"
echo -e "${BLUE}💡 Run 'docker compose up --build' to start fresh${NC}"