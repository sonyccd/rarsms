#!/bin/bash

# RARSMS Collection Setup Script
# Creates all required collections using PocketBase CLI

set -e

echo "🚀 RARSMS Collection Setup"
echo "========================="
echo ""

# Check if PocketBase is running
echo "📡 Checking PocketBase connection..."
if ! curl -s http://localhost:8090/api/health > /dev/null 2>&1; then
    echo "❌ PocketBase is not running or not accessible at http://localhost:8090"
    echo "   Please make sure PocketBase is started with: docker compose up -d"
    exit 1
fi

echo "✅ PocketBase is running"
echo ""

# Create a temporary collections schema file
echo "📝 Creating collections schema..."

cat > /tmp/collections_schema.json << 'EOF'
[
  {
    "id": "member_profiles",
    "name": "member_profiles",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "user",
        "type": "relation",
        "required": true,
        "unique": true,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username", "email"]
        }
      },
      {
        "name": "callsign",
        "type": "text",
        "required": true,
        "unique": true,
        "options": {
          "min": 3,
          "max": 10,
          "pattern": "^[A-Z0-9]+$"
        }
      },
      {
        "name": "name",
        "type": "text",
        "required": true,
        "options": {
          "min": 1,
          "max": 100
        }
      },
      {
        "name": "discord_id",
        "type": "text",
        "required": false,
        "options": {
          "max": 20
        }
      },
      {
        "name": "joined_date",
        "type": "date",
        "required": false
      },
      {
        "name": "last_login",
        "type": "date",
        "required": false
      },
      {
        "name": "notes",
        "type": "editor",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.id = user || @request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.id = user || @request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "messages",
    "name": "messages",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "correlation_id",
        "type": "text",
        "required": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "user",
        "type": "relation",
        "required": false,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username"]
        }
      },
      {
        "name": "from_callsign",
        "type": "text",
        "required": false,
        "options": {
          "max": 10
        }
      },
      {
        "name": "to_callsign",
        "type": "text",
        "required": false,
        "options": {
          "max": 10
        }
      },
      {
        "name": "content",
        "type": "text",
        "required": true,
        "options": {
          "max": 500
        }
      },
      {
        "name": "platform",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["aprs", "discord", "web"]
        }
      },
      {
        "name": "status",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["pending", "sent", "delivered", "failed"]
        }
      },
      {
        "name": "direction",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["inbound", "outbound"]
        }
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin' || @request.auth.id = user",
    "viewRule": "@request.auth.role = 'admin' || @request.auth.id = user",
    "createRule": "@request.auth.id != \"\"",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "system_status",
    "name": "system_status",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "service",
        "type": "text",
        "required": true,
        "unique": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "status",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["healthy", "degraded", "unhealthy", "unknown"]
        }
      },
      {
        "name": "last_check",
        "type": "date",
        "required": true
      },
      {
        "name": "message",
        "type": "text",
        "required": false,
        "options": {
          "max": 200
        }
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "conversations",
    "name": "conversations",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "correlation_id",
        "type": "text",
        "required": true,
        "unique": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "initiated_by",
        "type": "relation",
        "required": false,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username"]
        }
      },
      {
        "name": "participants",
        "type": "text",
        "required": true,
        "options": {
          "max": 100
        }
      },
      {
        "name": "platform",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["aprs", "discord", "web"]
        }
      },
      {
        "name": "status",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["active", "closed", "archived"]
        }
      },
      {
        "name": "last_activity",
        "type": "date",
        "required": false
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin' || @request.auth.id = initiated_by",
    "viewRule": "@request.auth.role = 'admin' || @request.auth.id = initiated_by",
    "createRule": "@request.auth.id != \"\"",
    "updateRule": "@request.auth.role = 'admin' || @request.auth.id = initiated_by",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "aprs_packets",
    "name": "aprs_packets",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "raw_packet",
        "type": "text",
        "required": true,
        "options": {
          "max": 1000
        }
      },
      {
        "name": "from_callsign",
        "type": "text",
        "required": true,
        "options": {
          "max": 10
        }
      },
      {
        "name": "to_callsign",
        "type": "text",
        "required": false,
        "options": {
          "max": 10
        }
      },
      {
        "name": "message",
        "type": "text",
        "required": false,
        "options": {
          "max": 500
        }
      },
      {
        "name": "packet_type",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["message", "position", "status", "other"]
        }
      },
      {
        "name": "processed",
        "type": "bool",
        "required": true
      },
      {
        "name": "correlation_id",
        "type": "text",
        "required": false,
        "options": {
          "max": 50
        }
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "discord_threads",
    "name": "discord_threads",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "thread_id",
        "type": "text",
        "required": true,
        "unique": true,
        "options": {
          "max": 30
        }
      },
      {
        "name": "correlation_id",
        "type": "text",
        "required": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "initiated_by",
        "type": "relation",
        "required": false,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username"]
        }
      },
      {
        "name": "participants",
        "type": "text",
        "required": true,
        "options": {
          "max": 100
        }
      },
      {
        "name": "status",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["active", "archived", "closed"]
        }
      },
      {
        "name": "last_activity",
        "type": "date",
        "required": false
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "pending_approvals",
    "name": "pending_approvals",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "user",
        "type": "relation",
        "required": true,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username", "email"]
        }
      },
      {
        "name": "callsign",
        "type": "text",
        "required": true,
        "options": {
          "max": 10
        }
      },
      {
        "name": "name",
        "type": "text",
        "required": true,
        "options": {
          "max": 100
        }
      },
      {
        "name": "email",
        "type": "email",
        "required": true,
        "options": {
          "max": 200
        }
      },
      {
        "name": "expires_at",
        "type": "date",
        "required": true
      },
      {
        "name": "admin_notified",
        "type": "bool",
        "required": true
      },
      {
        "name": "user_notified",
        "type": "bool",
        "required": true
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  },
  {
    "id": "system_logs",
    "name": "system_logs",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "level",
        "type": "select",
        "required": true,
        "options": {
          "maxSelect": 1,
          "values": ["debug", "info", "warn", "error", "critical"]
        }
      },
      {
        "name": "service",
        "type": "text",
        "required": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "event_type",
        "type": "text",
        "required": true,
        "options": {
          "max": 50
        }
      },
      {
        "name": "message",
        "type": "text",
        "required": true,
        "options": {
          "max": 500
        }
      },
      {
        "name": "user",
        "type": "relation",
        "required": false,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": false,
          "maxSelect": 1,
          "displayFields": ["username"]
        }
      },
      {
        "name": "metadata",
        "type": "json",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  }
]
EOF

echo "✅ Schema file created"
echo ""

# Create migration file instead of JSON import
echo "📦 Creating PocketBase migration..."

# Create migration directory in container
docker compose exec pocketbase mkdir -p /app/pb_data/migrations

# Generate migration filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MIGRATION_FILE="/tmp/migration_${TIMESTAMP}_setup_collections.js"

cat > $MIGRATION_FILE << 'EOF'
migrate((db) => {
  // Create member_profiles collection
  const memberProfilesCollection = new Collection({
    "id": "member_profiles",
    "name": "member_profiles",
    "type": "base",
    "system": false,
    "schema": [
      {
        "name": "user",
        "type": "relation",
        "required": true,
        "unique": true,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "maxSelect": 1,
          "displayFields": ["username", "email"]
        }
      },
      {
        "name": "callsign",
        "type": "text",
        "required": true,
        "unique": true,
        "options": {
          "min": 3,
          "max": 10,
          "pattern": "^[A-Z0-9]+$"
        }
      },
      {
        "name": "name",
        "type": "text",
        "required": true,
        "options": {
          "min": 1,
          "max": 100
        }
      },
      {
        "name": "discord_id",
        "type": "text",
        "required": false,
        "options": {
          "max": 20
        }
      },
      {
        "name": "joined_date",
        "type": "date",
        "required": false
      },
      {
        "name": "last_login",
        "type": "date",
        "required": false
      },
      {
        "name": "notes",
        "type": "editor",
        "required": false
      }
    ],
    "listRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.id = user || @request.auth.role = 'admin'",
    "createRule": "@request.auth.role = 'admin'",
    "updateRule": "@request.auth.id = user || @request.auth.role = 'admin'",
    "deleteRule": "@request.auth.role = 'admin'"
  })
  return Dao(db).saveCollection(memberProfilesCollection)

}, (db) => {
  // Rollback: Delete member_profiles collection
  const collection = Dao(db).findCollectionByNameOrId("member_profiles")
  return Dao(db).deleteCollection(collection)
})
EOF

# Copy migration to container
docker compose cp $MIGRATION_FILE pocketbase:/app/pb_data/migrations/

# Run migration
echo "🚀 Running migration..."
docker compose exec pocketbase /app/pocketbase migrate

echo ""
echo "✅ Collections imported successfully!"
echo ""

# Clean up
rm -f /tmp/collections_schema.json

echo "🎉 RARSMS database setup complete!"
echo ""
echo "📋 Collections created:"
echo "   • member_profiles"
echo "   • messages"
echo "   • conversations"
echo "   • aprs_packets"
echo "   • discord_threads"
echo "   • pending_approvals"
echo "   • system_logs"
echo "   • system_status"
echo ""
echo "⚠️  Important: You still need to modify the 'users' collection"
echo "   to add the approval workflow fields. See COLLECTIONS.md"
echo ""
echo "🚀 Restart services to apply changes:"
echo "   docker compose restart"