#!/usr/bin/env python3

import requests
import json

# PocketBase API endpoint
BASE_URL = "http://localhost:8090"

def update_collection_rules():
    """Update collection rules to allow public read access to messages"""

    # We need to update the messages collection to allow public reads
    collection_id = "rarsms_messages"

    # New rules - allow public read access but no write access
    rules_update = {
        "listRule": "",  # Empty string means public access
        "viewRule": "",  # Empty string means public access
        "createRule": None,  # null means no access (only admin/system can create)
        "updateRule": None,  # null means no access
        "deleteRule": None   # null means no access
    }

    try:
        # Get current collection info first
        response = requests.get(f"{BASE_URL}/api/collections/{collection_id}")
        if response.status_code != 200:
            print(f"❌ Failed to get collection info: {response.status_code}")
            return False

        current_collection = response.json()
        print(f"📋 Current collection: {current_collection['name']}")

        # Update the collection rules
        response = requests.patch(
            f"{BASE_URL}/api/collections/{collection_id}",
            json=rules_update,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print("✅ Successfully updated collection rules for public read access")
            print("   • listRule: '' (public)")
            print("   • viewRule: '' (public)")
            print("   • createRule: null (admin only)")
            return True
        else:
            print(f"❌ Failed to update collection rules: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception updating collection rules: {e}")
        return False

def main():
    print("🔧 RARSMS PocketBase Permissions Setup")
    print("=" * 50)

    if update_collection_rules():
        print("\n🎉 Setup complete!")
        print("📱 The live viewer should now work at: http://localhost:8090/")
    else:
        print("\n❌ Setup failed!")
        print("💡 You may need to set permissions manually in PocketBase admin:")
        print("   1. Go to http://localhost:8090/_/")
        print("   2. Open 'messages' collection")
        print("   3. Go to 'API Rules' tab")
        print("   4. Set 'List/Search rule' to: (empty)")
        print("   5. Set 'View rule' to: (empty)")

if __name__ == "__main__":
    main()