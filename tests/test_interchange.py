#!/usr/bin/env python3

import pytest
from datetime import datetime
from protocols.interchange import (
    UniversalMessage, ContentBlock, ContentPriority, MessageAdapter,
    create_text_message, create_position_message, create_emergency_message
)
from protocols.base import MessageType, ProtocolCapabilities

class TestUniversalMessage:
    """Test UniversalMessage functionality"""

    @pytest.fixture
    def sample_message(self):
        """Create a sample universal message"""
        return UniversalMessage(
            message_id="test123",
            source_protocol="aprs_main",
            source_id="W4ABC",
            timestamp=datetime(2025, 9, 23, 10, 30),
            message_type=MessageType.TEXT
        )

    def test_message_initialization(self, sample_message):
        """Test basic message initialization"""
        assert sample_message.message_id == "test123"
        assert sample_message.source_protocol == "aprs_main"
        assert sample_message.source_id == "W4ABC"
        assert sample_message.message_type == MessageType.TEXT
        assert len(sample_message.content_blocks) == 0

    def test_auto_generate_message_id(self):
        """Test automatic message ID generation"""
        message = UniversalMessage(
            message_id="",
            source_protocol="test",
            source_id="test",
            timestamp=datetime.utcnow(),
            message_type=MessageType.TEXT
        )
        assert message.message_id != ""
        assert len(message.message_id) == 8

    def test_add_content_block(self, sample_message):
        """Test adding content blocks"""
        sample_message.add_content_block(
            "Test message",
            ContentPriority.HIGH,
            "text"
        )

        assert len(sample_message.content_blocks) == 1
        block = sample_message.content_blocks[0]
        assert block.content == "Test message"
        assert block.priority == ContentPriority.HIGH
        assert block.content_type == "text"

    def test_add_text(self, sample_message):
        """Test convenience method for adding text"""
        sample_message.add_text("Hello world", ContentPriority.CRITICAL)

        assert len(sample_message.content_blocks) == 1
        block = sample_message.content_blocks[0]
        assert block.content == "Hello world"
        assert block.priority == ContentPriority.CRITICAL
        assert block.content_type == "text"

    def test_add_location(self, sample_message):
        """Test adding location information"""
        sample_message.add_location(35.7796, -78.6382, "Test location")

        # Should set position data
        assert sample_message.position == {'lat': 35.7796, 'lon': -78.6382}

        # Should add location content block
        assert len(sample_message.content_blocks) == 1
        block = sample_message.content_blocks[0]
        assert block.content == "Test location"
        assert block.content_type == "location"
        assert block.priority == ContentPriority.MEDIUM

    def test_add_location_without_description(self, sample_message):
        """Test adding location without description"""
        sample_message.add_location(35.7796, -78.6382)

        assert sample_message.position == {'lat': 35.7796, 'lon': -78.6382}
        assert len(sample_message.content_blocks) == 0

    def test_add_metadata(self, sample_message):
        """Test adding metadata"""
        sample_message.add_metadata("source_type", "emergency")

        # Should add to metadata dict
        assert sample_message.metadata["source_type"] == "emergency"

        # Should add content block
        assert len(sample_message.content_blocks) == 1
        block = sample_message.content_blocks[0]
        assert block.content == "source_type: emergency"
        assert block.content_type == "metadata"
        assert block.priority == ContentPriority.LOW
        assert block.can_omit is True

    def test_get_primary_content(self, sample_message):
        """Test getting primary content"""
        sample_message.add_text("Critical message", ContentPriority.CRITICAL)
        sample_message.add_text("High priority", ContentPriority.HIGH)
        sample_message.add_text("Medium priority", ContentPriority.MEDIUM)
        sample_message.add_metadata("test", "value")

        primary = sample_message.get_primary_content()
        assert "Critical message" in primary
        assert "High priority" in primary
        assert "Medium priority" not in primary
        assert "test: value" not in primary

    def test_get_full_content(self, sample_message):
        """Test getting all content concatenated"""
        sample_message.add_text("First", ContentPriority.HIGH)
        sample_message.add_text("Second", ContentPriority.MEDIUM)
        sample_message.add_metadata("key", "value")

        full = sample_message.get_full_content()
        assert "First" in full
        assert "Second" in full
        assert "key: value" in full

class TestContentBlock:
    """Test ContentBlock functionality"""

    def test_content_block_creation(self):
        """Test creating content blocks with various options"""
        block = ContentBlock(
            content="Test content",
            priority=ContentPriority.HIGH,
            content_type="text",
            min_length=5,
            can_truncate=False,
            can_omit=True,
            fallback_text="Fallback"
        )

        assert block.content == "Test content"
        assert block.priority == ContentPriority.HIGH
        assert block.content_type == "text"
        assert block.min_length == 5
        assert block.can_truncate is False
        assert block.can_omit is True
        assert block.fallback_text == "Fallback"

    def test_content_block_defaults(self):
        """Test default values for content blocks"""
        block = ContentBlock(
            content="Test",
            priority=ContentPriority.MEDIUM,
            content_type="text"
        )

        assert block.min_length == 0
        assert block.can_truncate is True
        assert block.can_omit is False
        assert block.fallback_text is None

class TestMessageAdapter:
    """Test MessageAdapter functionality"""

    @pytest.fixture
    def adapter(self):
        """Create message adapter instance"""
        return MessageAdapter()

    @pytest.fixture
    def sample_universal_message(self):
        """Create sample universal message for adaptation"""
        msg = UniversalMessage(
            message_id="test123",
            source_protocol="aprs_main",
            source_id="W4ABC",
            timestamp=datetime(2025, 9, 23, 10, 30),
            message_type=MessageType.TEXT
        )
        msg.add_text("Hello from the field!", ContentPriority.HIGH)
        msg.add_location(35.7796, -78.6382, "Mobile station")
        msg.add_metadata("source_type", "mobile")
        return msg

    def test_adapt_message_basic(self, adapter, sample_universal_message):
        """Test basic message adaptation"""
        capabilities = ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            max_message_length=200
        )

        adapted = adapter.adapt_message(
            sample_universal_message,
            capabilities,
            "test_protocol"
        )

        assert len(adapted) == 1
        message = adapted[0]
        assert message['source_protocol'] == "aprs_main"
        assert message['source_id'] == "W4ABC"
        assert "Hello from the field!" in message['content']

    def test_adapt_message_length_limit(self, adapter, sample_universal_message):
        """Test adaptation with strict length limits"""
        capabilities = ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            max_message_length=30  # Very short limit
        )

        adapted = adapter.adapt_message(
            sample_universal_message,
            capabilities,
            "test_protocol"
        )

        assert len(adapted) == 1
        message = adapted[0]
        assert len(message['content']) <= 30

    def test_adapt_for_aprs(self, adapter):
        """Test APRS-specific adaptations"""
        block = ContentBlock(
            content="Check this map: https://maps.google.com/?q=35.7,-78.6 *bold*",
            priority=ContentPriority.HIGH,
            content_type="location"
        )

        adapted_block = adapter._adapt_for_aprs(block)

        # Should remove map links and markdown
        assert "https://maps.google.com" not in adapted_block.content
        assert "*bold*" not in adapted_block.content

    def test_adapt_for_discord(self, adapter):
        """Test Discord-specific adaptations"""
        block = ContentBlock(
            content="Location: 35.7796,-78.6382",
            priority=ContentPriority.HIGH,
            content_type="location"
        )

        adapted_block = adapter._adapt_for_discord(block)

        # Should add Discord-friendly map formatting
        assert "maps.google.com" in adapted_block.content
        assert "📍" in adapted_block.content

    def test_smart_truncate_sentence_boundary(self, adapter):
        """Test smart truncation at sentence boundaries"""
        text = "First sentence. Second sentence. Third sentence."
        truncated = adapter._smart_truncate(text, 30)

        assert len(truncated) <= 30
        assert truncated.endswith("...")
        assert "First sentence." in truncated

    def test_smart_truncate_word_boundary(self, adapter):
        """Test smart truncation at word boundaries"""
        text = "This is a long message without periods"
        truncated = adapter._smart_truncate(text, 20)

        assert len(truncated) <= 20
        assert truncated.endswith("...")
        # Should break at word boundary
        assert not truncated[:-3].endswith(" ")

    def test_fit_to_protocol_limits_priority_order(self, adapter):
        """Test that content is included in priority order"""
        blocks = [
            ContentBlock("Low priority", ContentPriority.LOW, "text"),
            ContentBlock("Critical", ContentPriority.CRITICAL, "text"),
            ContentBlock("Medium priority", ContentPriority.MEDIUM, "text"),
            ContentBlock("High priority", ContentPriority.HIGH, "text"),
        ]

        capabilities = ProtocolCapabilities(max_message_length=25)  # Only fits critical + high
        fitted = adapter._fit_to_protocol_limits(blocks, capabilities)

        # Should include critical and high priority first
        contents = [block.content for block in fitted]
        assert "Critical" in contents
        assert "High priority" in contents

    def test_fit_to_protocol_limits_truncation(self, adapter):
        """Test content truncation when fitting to limits"""
        blocks = [
            ContentBlock(
                "This is a very long message that needs truncation",
                ContentPriority.CRITICAL,
                "text",
                can_truncate=True,
                min_length=10
            )
        ]

        capabilities = ProtocolCapabilities(max_message_length=20)
        fitted = adapter._fit_to_protocol_limits(blocks, capabilities)

        assert len(fitted) == 1
        assert len(fitted[0].content) <= 20
        assert fitted[0].content.endswith("...")

    def test_fit_to_protocol_limits_fallback_text(self, adapter):
        """Test using fallback text when content too long"""
        blocks = [
            ContentBlock(
                "This is a very long message that would be truncated",
                ContentPriority.HIGH,
                "text",
                can_truncate=False,
                fallback_text="Short fallback"
            )
        ]

        capabilities = ProtocolCapabilities(max_message_length=20)
        fitted = adapter._fit_to_protocol_limits(blocks, capabilities)

        assert len(fitted) == 1
        assert fitted[0].content == "Short fallback"

class TestConvenienceFunctions:
    """Test convenience functions for creating messages"""

    def test_create_text_message(self):
        """Test creating simple text message"""
        msg = create_text_message(
            "discord_main",
            "TestUser",
            "Hello world"
        )

        assert msg.source_protocol == "discord_main"
        assert msg.source_id == "TestUser"
        assert msg.message_type == MessageType.TEXT
        assert len(msg.content_blocks) == 1
        assert msg.content_blocks[0].content == "Hello world"
        assert msg.content_blocks[0].priority == ContentPriority.HIGH

    def test_create_position_message(self):
        """Test creating position message"""
        msg = create_position_message(
            "aprs_main",
            "W4ABC-9",
            35.7796,
            -78.6382,
            "Mobile station"
        )

        assert msg.source_protocol == "aprs_main"
        assert msg.source_id == "W4ABC-9"
        assert msg.message_type == MessageType.POSITION
        assert msg.position == {'lat': 35.7796, 'lon': -78.6382}

        # Should have location block and text block
        assert len(msg.content_blocks) == 2

        content_types = [block.content_type for block in msg.content_blocks]
        assert "location" in content_types
        assert "text" in content_types

    def test_create_position_message_no_comment(self):
        """Test creating position message without comment"""
        msg = create_position_message(
            "aprs_main",
            "W4ABC-9",
            35.7796,
            -78.6382
        )

        assert msg.position == {'lat': 35.7796, 'lon': -78.6382}
        # Should only have location block, no text
        assert len(msg.content_blocks) == 1
        assert msg.content_blocks[0].content_type == "location"

    def test_create_emergency_message(self):
        """Test creating emergency message"""
        msg = create_emergency_message(
            "aprs_main",
            "W4ABC",
            "Vehicle accident on I-40",
            35.7796,
            -78.6382
        )

        assert msg.source_protocol == "aprs_main"
        assert msg.source_id == "W4ABC"
        assert msg.message_type == MessageType.EMERGENCY
        assert msg.urgency == ContentPriority.CRITICAL
        assert msg.position == {'lat': 35.7796, 'lon': -78.6382}

        # Should have emergency text and location
        assert len(msg.content_blocks) == 2

        # Check emergency text block
        emergency_block = next(b for b in msg.content_blocks if "EMERGENCY" in b.content)
        assert emergency_block.priority == ContentPriority.CRITICAL
        assert "Vehicle accident on I-40" in emergency_block.content

    def test_create_emergency_message_no_location(self):
        """Test creating emergency message without location"""
        msg = create_emergency_message(
            "aprs_main",
            "W4ABC",
            "Vehicle accident on I-40"
        )

        assert msg.position is None
        assert len(msg.content_blocks) == 1
        assert "🚨 EMERGENCY" in msg.content_blocks[0].content

class TestContentPriority:
    """Test ContentPriority enum"""

    def test_priority_values(self):
        """Test priority enum values"""
        assert ContentPriority.CRITICAL.value == 1
        assert ContentPriority.HIGH.value == 2
        assert ContentPriority.MEDIUM.value == 3
        assert ContentPriority.LOW.value == 4

    def test_priority_ordering(self):
        """Test that priorities can be ordered"""
        priorities = [
            ContentPriority.LOW,
            ContentPriority.CRITICAL,
            ContentPriority.MEDIUM,
            ContentPriority.HIGH
        ]

        sorted_priorities = sorted(priorities, key=lambda x: x.value)

        assert sorted_priorities[0] == ContentPriority.CRITICAL
        assert sorted_priorities[1] == ContentPriority.HIGH
        assert sorted_priorities[2] == ContentPriority.MEDIUM
        assert sorted_priorities[3] == ContentPriority.LOW