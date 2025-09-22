#!/usr/bin/env python3

"""
Demonstration of the Universal Message Interchange Format

This example shows how messages can be created and adapted for different protocols
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocols.interchange import (
    UniversalMessage, MessageAdapter, ContentPriority,
    create_text_message, create_position_message, create_emergency_message
)
from protocols.base import ProtocolCapabilities, MessageType
from datetime import datetime

def demo_message_adaptation():
    """Demonstrate how messages adapt to different protocol capabilities"""

    print("🚀 Universal Message Interchange Format Demo")
    print("=" * 60)

    # Create a rich message with multiple content blocks
    universal_msg = UniversalMessage(
        message_id="demo-001",
        source_protocol="discord_main",
        source_id="user123",
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        urgency=ContentPriority.HIGH
    )

    # Add various content blocks
    universal_msg.add_text("Emergency meeting tonight at 7 PM", ContentPriority.HIGH)
    universal_msg.add_location(35.7796, -78.6382, "Raleigh, NC HQ", ContentPriority.MEDIUM)
    universal_msg.add_metadata("event_type", "club_meeting", ContentPriority.LOW)
    universal_msg.add_metadata("attendees", "all_members", ContentPriority.LOW)
    universal_msg.add_content_block(
        "Please confirm attendance by replying to this message",
        ContentPriority.MEDIUM,
        'text'
    )

    print("📝 Original Universal Message:")
    print(f"   Content blocks: {len(universal_msg.content_blocks)}")
    print(f"   Full content: {universal_msg.get_full_content()}")
    print(f"   Character count: {len(universal_msg.get_full_content())}")
    print()

    # Define different protocol capabilities
    protocols = {
        'APRS': ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            supports_position=True,
            supports_threading=False,
            supports_attachments=False,
            max_message_length=67  # APRS message limit
        ),
        'Discord': ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            supports_position=True,
            supports_threading=True,
            supports_attachments=True,
            max_message_length=2000  # Discord limit
        ),
    }

    # Create adapter
    adapter = MessageAdapter()

    # Adapt message for each protocol
    for protocol_name, capabilities in protocols.items():
        print(f"📡 Adapting for {protocol_name}:")
        print(f"   Max length: {capabilities.max_message_length}")
        print(f"   Position support: {capabilities.supports_position}")

        try:
            adapted_messages = adapter.adapt_message(
                universal_msg, capabilities, protocol_name.lower()
            )

            for i, adapted_msg in enumerate(adapted_messages):
                content = adapted_msg['content']
                print(f"   Message {i+1}: {content}")
                print(f"   Length: {len(content)}")

                if capabilities.max_message_length:
                    if len(content) <= capabilities.max_message_length:
                        print("   ✅ Fits within protocol limits")
                    else:
                        print("   ❌ Exceeds protocol limits!")

        except Exception as e:
            print(f"   ❌ Adaptation failed: {e}")

        print()

def demo_message_types():
    """Demonstrate different message types"""

    print("📨 Message Type Examples")
    print("=" * 40)

    # Text message
    text_msg = create_text_message(
        "discord_main", "user456",
        "Anyone know the frequency for the repeater?"
    )
    print(f"💬 Text: {text_msg.get_primary_content()}")

    # Position message
    pos_msg = create_position_message(
        "aprs_main", "W4ABC-9",
        35.7796, -78.6382,
        "Mobile station heading north"
    )
    print(f"📍 Position: {pos_msg.get_primary_content()}")
    print(f"    Location: {pos_msg.position}")

    # Emergency message
    emergency_msg = create_emergency_message(
        "aprs_main", "N4DEF",
        "Vehicle accident on I-40, need assistance",
        35.7500, -78.7000
    )
    print(f"🚨 Emergency: {emergency_msg.get_primary_content()}")
    print(f"    Urgency: {emergency_msg.urgency}")
    print()

def demo_content_priorities():
    """Demonstrate content priority system"""

    print("🎯 Content Priority Demo")
    print("=" * 30)

    # Create message with different priority content
    msg = UniversalMessage(
        message_id="priority-demo",
        source_protocol="test",
        source_id="demo",
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT
    )

    msg.add_content_block("CRITICAL: System failure", ContentPriority.CRITICAL, 'text')
    msg.add_content_block("Important update needed", ContentPriority.HIGH, 'text')
    msg.add_content_block("Meeting scheduled for tomorrow", ContentPriority.MEDIUM, 'text')
    msg.add_content_block("Weather is nice today", ContentPriority.LOW, 'text')

    print("All content blocks:")
    for i, block in enumerate(msg.content_blocks):
        print(f"  {i+1}. [{block.priority.name}] {block.content}")

    print()
    print("Adaptation for 50-character limit:")

    # Simulate very short message limit
    short_capabilities = ProtocolCapabilities(
        can_send=True,
        can_receive=True,
        supports_position=False,
        supports_threading=False,
        supports_attachments=False,
        max_message_length=50
    )

    adapter = MessageAdapter()
    adapted = adapter.adapt_message(msg, short_capabilities, "short_protocol")

    for adapted_msg in adapted:
        content = adapted_msg['content']
        print(f"  Adapted: {content}")
        print(f"  Length: {len(content)}/50")

if __name__ == "__main__":
    demo_message_adaptation()
    print()
    demo_message_types()
    print()
    demo_content_priorities()

    print("\n🎉 Demo complete!")
    print("The Universal Message Interchange Format allows:")
    print("  • Rich content with priority-based adaptation")
    print("  • Automatic fitting to protocol limitations")
    print("  • Protocol-specific formatting")
    print("  • Preservation of critical information")
    print("  • Graceful degradation for simple protocols")