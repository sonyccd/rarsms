#!/usr/bin/env python3

import sys
import asyncio
from datetime import datetime

# Add protocols to path
sys.path.append('.')

from protocols.pocketbase_protocol import PocketBaseProtocol
from protocols.base import Message, MessageType

async def test_pocketbase_integration():
    """Test PocketBase protocol integration"""
    print("🧪 Testing PocketBase Integration")
    print("=" * 50)

    # Create PocketBase protocol instance
    config = {
        'pocketbase_url': 'http://localhost:8090',
        'collection_name': 'messages'
    }

    pb_protocol = PocketBaseProtocol('test_pocketbase', config)

    # Test configuration
    print(f"✓ Protocol configured: {pb_protocol.is_configured()}")
    print(f"✓ Capabilities: send={pb_protocol.capabilities.can_send}, receive={pb_protocol.capabilities.can_receive}")

    # Test connection
    print("\n📡 Testing connection...")
    connected = await pb_protocol.connect()
    print(f"Connection result: {connected}")

    if not connected:
        print("❌ Could not connect to PocketBase")
        return False

    # Create test message
    print("\n📝 Creating test message...")
    test_message = Message(
        source_protocol='test_protocol',
        source_id='KK4TEST',
        message_type=MessageType.TEXT,
        content='Test message from PocketBase integration',
        timestamp=datetime.utcnow()
    )

    # Add some metadata
    test_message.metadata = {
        'raw_packet': 'KK4TEST>APRS,TCPIP*:>Test message from PocketBase integration'
    }

    # Store message
    stored = await pb_protocol.send_message(test_message)
    print(f"Message stored: {stored}")

    if stored:
        print("✅ PocketBase integration working correctly!")
    else:
        print("❌ Failed to store message")

    # Disconnect
    await pb_protocol.disconnect()
    return stored

if __name__ == "__main__":
    try:
        result = asyncio.run(test_pocketbase_integration())
        if result:
            print("\n🎉 Integration test passed!")
            print("💡 Now RARSMS can store messages in PocketBase")
            print("📱 Check http://localhost:8090/ to see the test message")
        else:
            print("\n❌ Integration test failed")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()