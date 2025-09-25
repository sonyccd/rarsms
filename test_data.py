#!/usr/bin/env python3

import requests
import json
from datetime import datetime, timedelta
import random
import time

# PocketBase API endpoint
BASE_URL = "http://localhost:8090"
COLLECTION = "messages"

# Sample APRS callsigns and messages
CALLSIGNS = [
    "KK4ABC-9", "W4DEF", "N0GHI-5", "KJ4JKL-1", "KC4MNO",
    "WA4PQR-10", "KB4STU", "N4VWX-7", "KD4YZ1", "WB4ABC-2"
]

SAMPLE_MESSAGES = [
    "Testing RARSMS bridge system",
    "Anyone on 146.52?",
    "QRT for dinner, 73",
    "Looking for net control",
    "Mobile and monitoring",
    "Testing new radio setup",
    "Good morning from the mobile",
    "Packet test successful",
    "Anyone copy?",
    "73 and safe travels"
]

# Raleigh area coordinates (for position messages)
RALEIGH_LAT = 35.7796
RALEIGH_LON = -78.6382

def generate_sample_message():
    """Generate a sample APRS message"""
    callsign = random.choice(CALLSIGNS)
    message_type = random.choices(
        ["text", "position", "status"],
        weights=[70, 20, 10]
    )[0]

    # Generate timestamp (recent past)
    now = datetime.utcnow()
    timestamp = now - timedelta(seconds=random.randint(0, 3600))

    data = {
        "message_id": f"msg_{int(time.time())}_{random.randint(1000, 9999)}",
        "source_protocol": "aprs_main",
        "source_id": callsign,
        "message_type": message_type,
        "timestamp": timestamp.isoformat() + "Z"
    }

    if message_type == "text":
        data["content"] = random.choice(SAMPLE_MESSAGES)

    elif message_type == "position":
        # Random position near Raleigh
        lat_offset = random.uniform(-0.5, 0.5)
        lon_offset = random.uniform(-0.5, 0.5)
        data["latitude"] = RALEIGH_LAT + lat_offset
        data["longitude"] = RALEIGH_LON + lon_offset
        data["content"] = f"Position update from {callsign}"

    elif message_type == "status":
        statuses = ["Mobile and monitoring", "QRV on repeater", "At home station", "Portable ops"]
        data["content"] = random.choice(statuses)

    # Add optional raw packet data
    data["raw_packet"] = f"{callsign}>APRS,TCPIP*:>{data['content']}"

    return data

def create_message(message_data):
    """Create a message in PocketBase"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/collections/{COLLECTION}/records",
            json=message_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"✓ Created message from {message_data['source_id']}: {message_data['content'][:50]}...")
            return True
        else:
            print(f"✗ Error creating message: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"✗ Exception creating message: {e}")
        return False

def main():
    print("🚀 RARSMS Test Data Generator")
    print("=" * 50)

    # Create some historical messages
    print("Creating initial test messages...")
    for i in range(10):
        message = generate_sample_message()
        create_message(message)
        time.sleep(0.1)  # Small delay

    print(f"\nCreated 10 test messages!")
    print("View them at: http://localhost:8090/")

    # Ask if user wants live simulation
    try:
        simulate = input("\nSimulate live messages? (y/N): ").lower().startswith('y')
        if simulate:
            print("\nSimulating live APRS traffic... (Press Ctrl+C to stop)")
            while True:
                message = generate_sample_message()
                # Make timestamp current for live effect
                message["timestamp"] = datetime.utcnow().isoformat() + "Z"

                if create_message(message):
                    # Random delay between messages (5-30 seconds)
                    delay = random.randint(5, 30)
                    print(f"   Waiting {delay} seconds for next message...")
                    time.sleep(delay)
                else:
                    break

    except KeyboardInterrupt:
        print("\n\n👋 Stopped simulation. Messages remain in database.")
    except Exception as e:
        print(f"\n❌ Error in simulation: {e}")

if __name__ == "__main__":
    main()