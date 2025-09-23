#!/usr/bin/env python3

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from protocols.base import Message, MessageType, ProtocolCapabilities, BaseProtocol

class TestMessage:
    """Test Message class functionality"""

    def test_message_basic_creation(self):
        """Test basic message creation with required fields"""
        msg = Message(
            source_protocol="test_protocol",
            source_id="test_user",
            message_type=MessageType.TEXT,
            content="Hello world"
        )

        assert msg.source_protocol == "test_protocol"
        assert msg.source_id == "test_user"
        assert msg.message_type == MessageType.TEXT
        assert msg.content == "Hello world"
        assert isinstance(msg.timestamp, datetime)
        assert isinstance(msg.metadata, dict)
        assert isinstance(msg.target_protocols, list)
        assert isinstance(msg.target_ids, dict)
        assert len(msg.message_id) == 8

    def test_message_with_custom_timestamp(self):
        """Test message creation with custom timestamp"""
        custom_time = datetime(2025, 9, 23, 10, 30, 0)
        msg = Message(
            source_protocol="test",
            source_id="user",
            message_type=MessageType.STATUS,
            content="Test",
            timestamp=custom_time
        )

        assert msg.timestamp == custom_time

    def test_message_with_metadata(self):
        """Test message creation with metadata"""
        metadata = {"source_type": "mobile", "priority": "high"}
        msg = Message(
            source_protocol="test",
            source_id="user",
            message_type=MessageType.TEXT,
            content="Test",
            metadata=metadata
        )

        assert msg.metadata == metadata

    def test_message_id_generation(self):
        """Test message ID generation is unique"""
        msg1 = Message("test", "user", MessageType.TEXT, "content1")
        msg2 = Message("test", "user", MessageType.TEXT, "content2")

        assert msg1.message_id != msg2.message_id
        assert len(msg1.message_id) == 8
        assert len(msg2.message_id) == 8

    def test_add_target_protocol(self):
        """Test adding target protocols for routing"""
        msg = Message("source", "user", MessageType.TEXT, "test")

        # Add protocol without target ID
        msg.add_target("discord")
        assert "discord" in msg.target_protocols
        assert len(msg.target_protocols) == 1

        # Add protocol with target ID
        msg.add_target("aprs", "W4ABC")
        assert "aprs" in msg.target_protocols
        assert msg.target_ids["aprs"] == "W4ABC"
        assert len(msg.target_protocols) == 2

    def test_add_target_duplicate_protocol(self):
        """Test adding same protocol multiple times"""
        msg = Message("source", "user", MessageType.TEXT, "test")

        msg.add_target("discord")
        msg.add_target("discord")  # Add again

        # Should only appear once
        assert msg.target_protocols.count("discord") == 1

    def test_get_position_for_position_message(self):
        """Test getting position data from position message"""
        position_data = {"lat": 35.7796, "lon": -78.6382}
        msg = Message(
            "aprs",
            "W4ABC",
            MessageType.POSITION,
            "Mobile station",
            metadata={"position": position_data}
        )

        pos = msg.get_position()
        assert pos == position_data

    def test_get_position_for_non_position_message(self):
        """Test getting position data from non-position message returns None"""
        msg = Message("discord", "user", MessageType.TEXT, "Hello")
        assert msg.get_position() is None

    def test_is_emergency(self):
        """Test emergency message detection"""
        emergency_msg = Message("aprs", "W4ABC", MessageType.EMERGENCY, "Help needed")
        text_msg = Message("discord", "user", MessageType.TEXT, "Hello")

        assert emergency_msg.is_emergency() is True
        assert text_msg.is_emergency() is False

    def test_to_dict(self):
        """Test message serialization to dictionary"""
        timestamp = datetime(2025, 9, 23, 10, 30, 0)
        msg = Message(
            "aprs_main",
            "W4ABC",
            MessageType.EMERGENCY,
            "Emergency message",
            timestamp=timestamp,
            metadata={"priority": "critical"}
        )
        msg.add_target("discord", "channel123")
        msg.thread_id = "thread456"
        msg.reply_to = "msg789"

        msg_dict = msg.to_dict()

        assert msg_dict["source_protocol"] == "aprs_main"
        assert msg_dict["source_id"] == "W4ABC"
        assert msg_dict["message_type"] == "emergency"
        assert msg_dict["content"] == "Emergency message"
        assert msg_dict["timestamp"] == "2025-09-23T10:30:00"
        assert msg_dict["metadata"] == {"priority": "critical"}
        assert msg_dict["target_protocols"] == ["discord"]
        assert msg_dict["target_ids"] == {"discord": "channel123"}
        assert msg_dict["thread_id"] == "thread456"
        assert msg_dict["reply_to"] == "msg789"
        assert "message_id" in msg_dict

class TestProtocolCapabilities:
    """Test ProtocolCapabilities class"""

    def test_default_capabilities(self):
        """Test default capability values"""
        caps = ProtocolCapabilities()

        assert caps.can_send is True
        assert caps.can_receive is True
        assert caps.supports_position is False
        assert caps.supports_threading is False
        assert caps.supports_attachments is False
        assert caps.max_message_length is None

    def test_custom_capabilities(self):
        """Test setting custom capabilities"""
        caps = ProtocolCapabilities(
            can_send=False,
            can_receive=True,
            supports_position=True,
            supports_threading=True,
            supports_attachments=False,
            max_message_length=280
        )

        assert caps.can_send is False
        assert caps.can_receive is True
        assert caps.supports_position is True
        assert caps.supports_threading is True
        assert caps.supports_attachments is False
        assert caps.max_message_length == 280

class TestMessageType:
    """Test MessageType enum"""

    def test_message_type_values(self):
        """Test message type enum values"""
        assert MessageType.TEXT.value == "text"
        assert MessageType.POSITION.value == "position"
        assert MessageType.STATUS.value == "status"
        assert MessageType.EMERGENCY.value == "emergency"

    def test_message_type_comparison(self):
        """Test message type comparison"""
        assert MessageType.TEXT == MessageType.TEXT
        assert MessageType.TEXT != MessageType.POSITION

# Mock implementation of BaseProtocol for testing
class MockProtocol(BaseProtocol):
    """Mock protocol implementation for testing"""

    def __init__(self, name: str, config: dict, capabilities: ProtocolCapabilities):
        self._test_capabilities = capabilities
        super().__init__(name, config)
        self.connected = False
        self.sent_messages = []

    def get_capabilities(self) -> ProtocolCapabilities:
        return self._test_capabilities

    async def connect(self) -> bool:
        self.connected = True
        self.is_connected = True
        return True

    async def disconnect(self) -> bool:
        self.connected = False
        self.is_connected = False
        return True

    async def send_message(self, message: Message) -> bool:
        self.sent_messages.append(message)
        return True

    def is_configured(self) -> bool:
        return True

class TestBaseProtocol:
    """Test BaseProtocol abstract base class functionality"""

    @pytest.fixture
    def basic_capabilities(self):
        """Basic protocol capabilities for testing"""
        return ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            max_message_length=100
        )

    @pytest.fixture
    def mock_protocol(self, basic_capabilities):
        """Create mock protocol instance"""
        return MockProtocol("test_protocol", {"key": "value"}, basic_capabilities)

    def test_protocol_initialization(self, mock_protocol):
        """Test protocol initialization"""
        assert mock_protocol.name == "test_protocol"
        assert mock_protocol.config == {"key": "value"}
        assert mock_protocol.is_connected is False
        assert mock_protocol.message_callback is None
        assert isinstance(mock_protocol.capabilities, ProtocolCapabilities)

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, mock_protocol):
        """Test connect and disconnect functionality"""
        # Initially not connected
        assert mock_protocol.is_connected is False

        # Connect
        result = await mock_protocol.connect()
        assert result is True
        assert mock_protocol.is_connected is True

        # Disconnect
        result = await mock_protocol.disconnect()
        assert result is True
        assert mock_protocol.is_connected is False

    def test_set_message_callback(self, mock_protocol):
        """Test setting message callback"""
        callback = Mock()
        mock_protocol.set_message_callback(callback)

        assert mock_protocol.message_callback == callback

    def test_on_message_received_with_callback(self, mock_protocol):
        """Test message callback invocation"""
        callback = Mock()
        mock_protocol.set_message_callback(callback)

        test_message = Message("source", "user", MessageType.TEXT, "test")
        mock_protocol.on_message_received(test_message)

        callback.assert_called_once_with(test_message)

    def test_on_message_received_without_callback(self, mock_protocol):
        """Test message received without callback doesn't crash"""
        test_message = Message("source", "user", MessageType.TEXT, "test")
        # Should not raise an exception
        mock_protocol.on_message_received(test_message)

    def test_validate_message_success(self, mock_protocol):
        """Test successful message validation"""
        message = Message("source", "user", MessageType.TEXT, "Short message")

        is_valid, error_msg = mock_protocol.validate_message(message)

        assert is_valid is True
        assert error_msg == "Message is valid"

    def test_validate_message_too_long(self, mock_protocol):
        """Test message validation failure for too long message"""
        long_content = "x" * 150  # Exceeds 100 char limit
        message = Message("source", "user", MessageType.TEXT, long_content)

        is_valid, error_msg = mock_protocol.validate_message(message)

        assert is_valid is False
        assert "Message too long" in error_msg
        assert "max: 100" in error_msg

    def test_validate_message_cannot_send(self):
        """Test message validation when protocol cannot send"""
        no_send_caps = ProtocolCapabilities(can_send=False)
        protocol = MockProtocol("test", {}, no_send_caps)

        message = Message("source", "user", MessageType.TEXT, "test")
        is_valid, error_msg = protocol.validate_message(message)

        assert is_valid is False
        assert "does not support sending messages" in error_msg

    def test_validate_message_unsupported_position(self, mock_protocol):
        """Test message validation for unsupported position message"""
        position_message = Message("source", "user", MessageType.POSITION, "At location")

        is_valid, error_msg = mock_protocol.validate_message(position_message)

        assert is_valid is False
        assert "does not support position messages" in error_msg

    def test_validate_message_position_supported(self):
        """Test message validation when position is supported"""
        position_caps = ProtocolCapabilities(supports_position=True)
        protocol = MockProtocol("test", {}, position_caps)

        position_message = Message("source", "user", MessageType.POSITION, "At location")
        is_valid, error_msg = protocol.validate_message(position_message)

        assert is_valid is True
        assert error_msg == "Message is valid"

    def test_format_message_for_protocol_text(self, mock_protocol):
        """Test default message formatting for text message"""
        message = Message("aprs_main", "W4ABC", MessageType.TEXT, "Hello world")

        formatted = mock_protocol.format_message_for_protocol(message)

        assert formatted == "[aprs_main] W4ABC: Hello world"

    def test_format_message_for_protocol_position(self, mock_protocol):
        """Test default message formatting for position message"""
        message = Message(
            "aprs_main",
            "W4ABC-9",
            MessageType.POSITION,
            "Mobile station",
            metadata={"position": {"lat": 35.7796, "lon": -78.6382}}
        )

        formatted = mock_protocol.format_message_for_protocol(message)

        assert "[aprs_main] W4ABC-9: Mobile station" in formatted
        assert "(Location: 35.7796, -78.6382)" in formatted

    def test_parse_incoming_message_default(self, mock_protocol):
        """Test default implementation of parse_incoming_message returns None"""
        result = mock_protocol.parse_incoming_message("raw_data")
        assert result is None

    def test_get_protocol_info(self, mock_protocol):
        """Test getting protocol information"""
        info = mock_protocol.get_protocol_info()

        expected_info = {
            'name': 'test_protocol',
            'connected': False,
            'capabilities': {
                'can_send': True,
                'can_receive': True,
                'supports_position': False,
                'supports_threading': False,
                'supports_attachments': False,
                'max_message_length': 100
            }
        }

        assert info == expected_info

    def test_protocol_string_representation(self, mock_protocol):
        """Test string representation of protocol"""
        string_repr = str(mock_protocol)
        assert string_repr == "MockProtocol(test_protocol)"

    @pytest.mark.asyncio
    async def test_send_message_tracking(self, mock_protocol):
        """Test that mock protocol tracks sent messages"""
        message1 = Message("source", "user1", MessageType.TEXT, "first")
        message2 = Message("source", "user2", MessageType.TEXT, "second")

        await mock_protocol.send_message(message1)
        await mock_protocol.send_message(message2)

        assert len(mock_protocol.sent_messages) == 2
        assert mock_protocol.sent_messages[0] == message1
        assert mock_protocol.sent_messages[1] == message2

class TestBaseProtocolEdgeCases:
    """Test edge cases and error conditions for BaseProtocol"""

    def test_validate_message_no_max_length(self):
        """Test validation when no max length is set"""
        unlimited_caps = ProtocolCapabilities(max_message_length=None)
        protocol = MockProtocol("test", {}, unlimited_caps)

        long_message = Message("source", "user", MessageType.TEXT, "x" * 10000)
        is_valid, error_msg = protocol.validate_message(long_message)

        # Should be valid since no limit is set
        assert is_valid is True

    def test_format_position_message_without_position_data(self, basic_capabilities):
        """Test formatting position message that lacks position metadata"""
        protocol = MockProtocol("test", {}, basic_capabilities)
        message = Message("source", "user", MessageType.POSITION, "Position update")
        # No position metadata

        formatted = protocol.format_message_for_protocol(message)

        # Should not crash and should not include location info
        assert formatted == "[source] user: Position update"
        assert "Location:" not in formatted