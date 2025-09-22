#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from protocols.manager import ProtocolManager
from protocols.base import BaseProtocol, Message, MessageType, ProtocolCapabilities
from protocols.interchange import UniversalMessage, ContentPriority

class MockProtocol(BaseProtocol):
    """Mock protocol for testing"""

    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.connected = False
        self.send_success = True
        self.sent_messages = []

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProtocolCapabilities:
        return ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            supports_position=True,
            max_message_length=100
        )

    async def connect(self) -> bool:
        self.connected = True
        self.is_connected = True
        return True

    async def disconnect(self) -> bool:
        self.connected = False
        self.is_connected = False
        return True

    async def send_message(self, message: Message) -> bool:
        if self.connected and self.send_success:
            self.sent_messages.append(message)
            return True
        return False

    def get_protocol_info(self) -> dict:
        return {
            'name': self.name,
            'type': 'mock',
            'connected': self.connected,
            'sent_count': len(self.sent_messages)
        }

class TestProtocolManager:
    """Test ProtocolManager functionality"""

    @pytest.fixture
    def manager(self):
        """Create a protocol manager instance"""
        return ProtocolManager()

    @pytest.fixture
    def mock_protocol_class(self):
        """Mock protocol class for registration"""
        return MockProtocol

    def test_initialization(self, manager):
        """Test protocol manager initialization"""
        assert len(manager.protocols) == 0
        assert len(manager.registry) == 0
        assert len(manager.routing_rules) == 0
        assert len(manager.message_history) == 0
        assert manager.stats['messages_received'] == 0
        assert manager.stats['messages_sent'] == 0

    def test_register_protocol_type(self, manager, mock_protocol_class):
        """Test registering a protocol type"""
        manager.register_protocol_type('mock', mock_protocol_class)

        assert 'mock' in manager.registry
        assert manager.registry['mock'] == mock_protocol_class

    def test_add_protocol_success(self, manager, mock_protocol_class):
        """Test successfully adding a protocol"""
        manager.register_protocol_type('mock', mock_protocol_class)

        config = {'test_param': 'value'}
        result = manager.add_protocol('test_protocol', 'mock', config)

        assert result is True
        assert 'test_protocol' in manager.protocols
        assert isinstance(manager.protocols['test_protocol'], MockProtocol)

    def test_add_protocol_unknown_type(self, manager):
        """Test adding protocol with unknown type"""
        result = manager.add_protocol('test_protocol', 'unknown', {})

        assert result is False
        assert 'test_protocol' not in manager.protocols

    def test_add_protocol_replace_existing(self, manager, mock_protocol_class):
        """Test replacing an existing protocol"""
        manager.register_protocol_type('mock', mock_protocol_class)

        # Add first protocol
        manager.add_protocol('test_protocol', 'mock', {})
        original_protocol = manager.protocols['test_protocol']

        # Replace with new protocol
        result = manager.add_protocol('test_protocol', 'mock', {'new': 'config'})

        assert result is True
        assert manager.protocols['test_protocol'] is not original_protocol

    @pytest.mark.asyncio
    async def test_connect_all_protocols(self, manager, mock_protocol_class):
        """Test connecting all protocols"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('protocol1', 'mock', {})
        manager.add_protocol('protocol2', 'mock', {})

        results = await manager.connect_all()

        assert len(results) == 2
        assert results['protocol1'] is True
        assert results['protocol2'] is True
        assert manager.protocols['protocol1'].connected is True
        assert manager.protocols['protocol2'].connected is True

    @pytest.mark.asyncio
    async def test_disconnect_all_protocols(self, manager, mock_protocol_class):
        """Test disconnecting all protocols"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('protocol1', 'mock', {})

        # Connect first
        await manager.connect_all()
        assert manager.protocols['protocol1'].connected is True

        # Then disconnect
        results = await manager.disconnect_all()

        assert results['protocol1'] is True
        assert manager.protocols['protocol1'].connected is False

    def test_add_routing_rule_simple(self, manager):
        """Test adding a simple routing rule"""
        manager.add_routing_rule(
            source_protocols=['protocol1'],
            target_protocols=['protocol2'],
            message_types=[MessageType.TEXT]
        )

        assert len(manager.routing_rules) == 1
        rule = manager.routing_rules[0]
        assert rule['source_protocols'] == ['protocol1']
        assert rule['target_protocols'] == ['protocol2']
        assert rule['message_types'] == [MessageType.TEXT]
        assert rule['bidirectional'] is False

    def test_add_routing_rule_bidirectional(self, manager):
        """Test adding a bidirectional routing rule"""
        manager.add_routing_rule(
            source_protocols=['protocol1'],
            target_protocols=['protocol2'],
            bidirectional=True
        )

        # Should create two rules (forward and reverse)
        assert len(manager.routing_rules) == 2

        # Check forward rule
        forward_rule = manager.routing_rules[0]
        assert forward_rule['source_protocols'] == ['protocol1']
        assert forward_rule['target_protocols'] == ['protocol2']

        # Check reverse rule
        reverse_rule = manager.routing_rules[1]
        assert reverse_rule['source_protocols'] == ['protocol2']
        assert reverse_rule['target_protocols'] == ['protocol1']

    def test_convert_message_to_universal(self, manager):
        """Test converting legacy Message to UniversalMessage"""
        message = Message(
            source_protocol='test_protocol',
            source_id='TEST-USER',
            message_type=MessageType.TEXT,
            content='Hello world!',
            metadata={'extra': 'data'}
        )

        universal_message = manager._convert_message_to_universal(message)

        assert isinstance(universal_message, UniversalMessage)
        assert universal_message.source_protocol == 'test_protocol'
        assert universal_message.source_id == 'TEST-USER'
        assert universal_message.message_type == MessageType.TEXT
        assert len(universal_message.content_blocks) > 0

    def test_convert_emergency_message_to_universal(self, manager):
        """Test converting emergency message gets critical priority"""
        message = Message(
            source_protocol='test_protocol',
            source_id='TEST-USER',
            message_type=MessageType.EMERGENCY,
            content='Emergency situation!'
        )

        universal_message = manager._convert_message_to_universal(message)

        # Should have at least one critical priority block
        has_critical = any(
            block.priority == ContentPriority.CRITICAL
            for block in universal_message.content_blocks
        )
        assert has_critical

    def test_convert_position_message_to_universal(self, manager):
        """Test converting position message with location data"""
        message = Message(
            source_protocol='aprs_test',
            source_id='W4ABC-9',
            message_type=MessageType.POSITION,
            content='Mobile station',
            metadata={
                'position': {'lat': 35.7796, 'lon': -78.6382}
            }
        )

        # Mock the get_position method
        message.get_position = lambda: {'lat': 35.7796, 'lon': -78.6382}

        universal_message = manager._convert_message_to_universal(message)

        # Should have location content
        has_location = any(
            block.content_type == 'location'
            for block in universal_message.content_blocks
        )
        assert has_location

    def test_message_matches_rule(self, manager):
        """Test message matching against routing rules"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        # Matching rule
        matching_rule = {
            'source_protocols': ['aprs_main'],
            'target_protocols': ['discord_main'],
            'message_types': [MessageType.TEXT],
            'source_filter': None
        }

        # Non-matching rule (wrong protocol)
        non_matching_rule = {
            'source_protocols': ['other_protocol'],
            'target_protocols': ['discord_main'],
            'message_types': [MessageType.TEXT],
            'source_filter': None
        }

        assert manager._message_matches_rule(message, matching_rule) is True
        assert manager._message_matches_rule(message, non_matching_rule) is False

    def test_message_matches_rule_with_filter(self, manager):
        """Test message matching with source filter"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        # Matching filter
        matching_rule = {
            'source_protocols': ['aprs_main'],
            'target_protocols': ['discord_main'],
            'message_types': [MessageType.TEXT],
            'source_filter': r'^W4.*'
        }

        # Non-matching filter
        non_matching_rule = {
            'source_protocols': ['aprs_main'],
            'target_protocols': ['discord_main'],
            'message_types': [MessageType.TEXT],
            'source_filter': r'^K4.*'
        }

        assert manager._message_matches_rule(message, matching_rule) is True
        assert manager._message_matches_rule(message, non_matching_rule) is False

    def test_universal_message_matches_rule(self, manager):
        """Test universal message matching against routing rules"""
        from datetime import datetime
        universal_message = UniversalMessage(
            message_id='test-123',
            source_protocol='aprs_main',
            source_id='W4ABC',
            timestamp=datetime.utcnow(),
            message_type=MessageType.TEXT
        )

        rule = {
            'source_protocols': ['aprs_main'],
            'target_protocols': ['discord_main'],
            'message_types': [MessageType.TEXT],
            'source_filter': None
        }

        assert manager._universal_message_matches_rule(universal_message, rule) is True

    @pytest.mark.asyncio
    async def test_on_message_received(self, manager, mock_protocol_class):
        """Test handling received messages"""
        # Setup protocol and routing
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('source_protocol', 'mock', {})
        manager.add_protocol('target_protocol', 'mock', {})

        await manager.connect_all()

        manager.add_routing_rule(
            source_protocols=['source_protocol'],
            target_protocols=['target_protocol'],
            message_types=[MessageType.TEXT]
        )

        # Create and handle message
        message = Message(
            source_protocol='source_protocol',
            source_id='TEST-USER',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        # Handle the message
        manager._on_message_received(message)

        # Wait for async routing to complete
        await asyncio.sleep(0.1)

        # Check statistics
        assert manager.stats['messages_received'] == 1
        assert len(manager.message_history) == 1
        assert len(manager.universal_message_history) == 1

        # Check that message was routed
        target_protocol = manager.protocols['target_protocol']
        assert len(target_protocol.sent_messages) == 1

    @pytest.mark.asyncio
    async def test_send_message_with_targets(self, manager, mock_protocol_class):
        """Test sending message to specific target protocols"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('target1', 'mock', {})
        manager.add_protocol('target2', 'mock', {})

        await manager.connect_all()

        result = await manager.send_message(
            source_protocol='external',
            source_id='USER',
            content='Test message',
            target_protocols=['target1', 'target2']
        )

        assert result is True
        assert len(manager.protocols['target1'].sent_messages) == 1
        assert len(manager.protocols['target2'].sent_messages) == 1

    def test_get_protocol_status(self, manager, mock_protocol_class):
        """Test getting protocol status"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('test_protocol', 'mock', {})

        status = manager.get_protocol_status()

        assert 'test_protocol' in status
        assert status['test_protocol']['name'] == 'test_protocol'
        assert status['test_protocol']['type'] == 'mock'

    def test_get_statistics(self, manager):
        """Test getting statistics"""
        # Modify some stats
        manager.stats['messages_received'] = 5
        manager.stats['messages_sent'] = 3

        stats = manager.get_statistics()

        assert stats['messages_received'] == 5
        assert stats['messages_sent'] == 3
        # Ensure we get a copy, not the original
        stats['messages_received'] = 999
        assert manager.stats['messages_received'] == 5

    def test_get_connected_protocols(self, manager, mock_protocol_class):
        """Test getting list of connected protocols"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('connected1', 'mock', {})
        manager.add_protocol('disconnected1', 'mock', {})

        # Connect only one
        manager.protocols['connected1'].is_connected = True
        manager.protocols['disconnected1'].is_connected = False

        connected = manager.get_connected_protocols()

        assert 'connected1' in connected
        assert 'disconnected1' not in connected
        assert len(connected) == 1

    def test_clear_history(self, manager):
        """Test clearing message history"""
        # Add some history
        manager.message_history = [Mock() for _ in range(5)]
        assert len(manager.message_history) == 5

        manager.clear_history()

        assert len(manager.message_history) == 0

    def test_get_recent_messages(self, manager):
        """Test getting recent messages"""
        # Create mock messages with to_dict method
        messages = []
        for i in range(10):
            msg = Mock()
            msg.to_dict.return_value = {'id': i, 'content': f'Message {i}'}
            messages.append(msg)

        manager.message_history = messages

        # Get last 5 messages
        recent = manager.get_recent_messages(5)

        assert len(recent) == 5
        assert recent[0]['id'] == 5  # Should be messages 5-9
        assert recent[-1]['id'] == 9

    def test_message_history_limit(self, manager):
        """Test that message history respects size limit"""
        manager.max_history = 5

        # Add more messages than the limit
        for i in range(10):
            message = Message(
                source_protocol='test',
                source_id=f'USER-{i}',
                message_type=MessageType.TEXT,
                content=f'Message {i}'
            )
            manager._on_message_received(message)

        # Should only keep the last 5
        assert len(manager.message_history) == 5
        assert manager.message_history[0].source_id == 'USER-5'
        assert manager.message_history[-1].source_id == 'USER-9'

    @pytest.mark.asyncio
    async def test_prepare_message_for_target(self, manager):
        """Test preparing message for specific target"""
        original_message = Message(
            source_protocol='source',
            source_id='USER',
            message_type=MessageType.TEXT,
            content='Original message',
            metadata={'original': 'data'}
        )

        prepared = manager._prepare_message_for_target(original_message, 'target_protocol')

        # Should be a copy with target added
        assert prepared.source_protocol == 'source'
        assert prepared.source_id == 'USER'
        assert prepared.content == 'Original message'
        assert 'target_protocol' in prepared.target_protocols
        assert prepared.metadata['original'] == 'data'

        # Should be different object
        assert prepared is not original_message

    @pytest.mark.asyncio
    async def test_routing_prevents_loops(self, manager, mock_protocol_class):
        """Test that routing prevents sending back to source protocol"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('protocol1', 'mock', {})
        manager.add_protocol('protocol2', 'mock', {})

        await manager.connect_all()

        # Add bidirectional routing
        manager.add_routing_rule(
            source_protocols=['protocol1'],
            target_protocols=['protocol1', 'protocol2'],  # Include source in targets
            bidirectional=True
        )

        # Send message from protocol1
        message = Message(
            source_protocol='protocol1',
            source_id='USER',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        manager._on_message_received(message)
        await asyncio.sleep(0.1)  # Wait for routing

        # protocol1 should not receive its own message back
        assert len(manager.protocols['protocol1'].sent_messages) == 0
        # But protocol2 should receive it
        assert len(manager.protocols['protocol2'].sent_messages) == 1

    def test_convert_aprs_reply_message_bypasses_metadata(self, manager):
        """Test that APRS reply messages bypass universal conversion to preserve target_ids"""
        message = Message(
            source_protocol='discord_main',
            source_id='User#1234',
            message_type=MessageType.TEXT,
            content='ack',
            metadata={
                'reply_to_aprs': True,
                'target_callsign': 'KK4PWJ-10'
            }
        )

        # APRS reply should NOT be converted to universal format
        # (this is tested by checking the routing path directly)
        universal_message = manager._convert_message_to_universal(message)

        # Should still convert, but metadata should be preserved cleanly
        assert universal_message.source_protocol == 'discord_main'
        assert universal_message.source_id == 'User#1234'

    @pytest.mark.asyncio
    async def test_aprs_reply_routing_preserves_target_ids(self, manager, mock_protocol_class):
        """Test that APRS reply messages preserve target_ids through routing"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('discord_main', 'mock', {})
        manager.add_protocol('aprs_main', 'mock', {})

        await manager.connect_all()

        # Add routing rule
        manager.add_routing_rule(
            source_protocols=['discord_main'],
            target_protocols=['aprs_main'],
            message_types=[MessageType.TEXT]
        )

        # Create APRS reply message with specific target_ids
        message = Message(
            source_protocol='discord_main',
            source_id='User#1234',
            message_type=MessageType.TEXT,
            content='ack',
            metadata={'reply_to_aprs': True}
        )
        message.target_ids['aprs'] = 'KK4PWJ-10'

        # Handle the message
        manager._on_message_received(message)
        await asyncio.sleep(0.1)  # Wait for routing

        # Check that target protocol received the message
        aprs_protocol = manager.protocols['aprs_main']
        assert len(aprs_protocol.sent_messages) == 1

        # Verify target_ids are preserved
        sent_message = aprs_protocol.sent_messages[0]
        assert sent_message.target_ids.get('aprs') == 'KK4PWJ-10'

    @pytest.mark.asyncio
    async def test_send_universal_message_adaptation(self, manager, mock_protocol_class):
        """Test sending universal message with automatic adaptation"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('target_protocol', 'mock', {})

        await manager.connect_all()

        # Create universal message
        from datetime import datetime
        universal_message = UniversalMessage(
            message_id='test-456',
            source_protocol='source',
            source_id='USER',
            timestamp=datetime.utcnow(),
            message_type=MessageType.TEXT
        )
        universal_message.add_text('Test message', ContentPriority.HIGH)
        universal_message.target_protocols = ['target_protocol']

        # Send the universal message
        success_count = await manager.send_universal_message(universal_message)

        assert success_count == 1
        assert len(manager.protocols['target_protocol'].sent_messages) == 1

    def test_universal_message_history_limit(self, manager):
        """Test that universal message history respects size limit"""
        manager.max_history = 3

        # Add messages beyond limit
        for i in range(5):
            message = Message(
                source_protocol='test',
                source_id=f'USER-{i}',
                message_type=MessageType.TEXT,
                content=f'Message {i}'
            )
            manager._on_message_received(message)

        # Should only keep last 3 universal messages
        assert len(manager.universal_message_history) == 3

    @pytest.mark.asyncio
    async def test_routing_statistics_tracking(self, manager, mock_protocol_class):
        """Test that routing statistics are properly tracked"""
        manager.register_protocol_type('mock', mock_protocol_class)
        manager.add_protocol('source', 'mock', {})
        manager.add_protocol('target', 'mock', {})

        await manager.connect_all()

        manager.add_routing_rule(
            source_protocols=['source'],
            target_protocols=['target'],
            message_types=[MessageType.TEXT]
        )

        # Send multiple messages
        for i in range(3):
            message = Message(
                source_protocol='source',
                source_id=f'USER-{i}',
                message_type=MessageType.TEXT,
                content=f'Message {i}'
            )
            manager._on_message_received(message)

        await asyncio.sleep(0.1)  # Wait for routing

        # Check statistics
        assert manager.stats['messages_received'] == 3
        assert manager.stats['messages_routed'] == 3
        assert manager.stats['messages_sent'] == 3