#!/usr/bin/env python3

import requests
import json
from datetime import datetime
import time
import random

# PocketBase API endpoint
BASE_URL = "http://localhost:8090"
COLLECTION = "messages"

def create_live_message():
    """Create a live test message to verify WebSocket updates"""

    callsigns = ["KK4ABC-9", "W4DEF", "N0GHI-5"]
    messages = [
        "Testing live updates",
        "Anyone on 146.52?",
        "Mobile and monitoring",
        "QSL QRT 73"
    ]

    data = {
        "message_id": f"live_{int(time.time())}_{random.randint(1000, 9999)}",
        "source_protocol": "aprs_main",
        "source_id": random.choice(callsigns),
        "message_type": "text",
        "content": random.choice(messages),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "latitude": 0,
        "longitude": 0,
        "thread_id": "",
        "reply_to": "",
        "target_protocols": None,
        "metadata": None,
        "raw_packet": f"{random.choice(callsigns)}>APRS,TCPIP*:>{random.choice(messages)}"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/collections/{COLLECTION}/records",
            json=data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"✅ Created live message from {data['source_id']}")
            print(f"   Message: {data['content']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔴 LIVE Message Test for WebSocket Updates")
    print("=" * 50)
    print("This will create messages in real-time to test the live viewer")
    print("Open http://localhost:8090/ in your browser to watch!")
    print()

    try:
        for i in range(5):
            print(f"Sending message {i+1}/5...")
            create_live_message()
            time.sleep(3)  # 3 second delay between messages

        print("\n✅ Test complete!")
        print("💡 Check the live viewer - you should see 5 new messages")

    except KeyboardInterrupt:
        print("\n👋 Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()