#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from protocols.aprs import APRSProtocol
from protocols.base import Message, MessageType, ProtocolCapabilities

class TestAPRSProtocol:
    """Test APRS protocol functionality"""

    @pytest.fixture
    def aprs_config(self):
        """Sample APRS configuration"""
        return {
            'aprs_server': 'test.aprs.net',
            'aprs_port': 14580,
            'aprs_callsign': 'W4TEST',
            'aprs_passcode': '12345',
            'filter_lat': '35.7796',
            'filter_lon': '-78.6382',
            'filter_distance': '100',
            'authorized_callsigns': ['W4ABC', 'KJ4XYZ', 'N4DEF'],
            'message_prefix': 'RARSMS',
            'require_prefix': True
        }

    @pytest.fixture
    def aprs_protocol(self, aprs_config):
        """Create APRS protocol instance"""
        return APRSProtocol('aprs_test', aprs_config)

    def test_protocol_initialization(self, aprs_protocol, aprs_config):
        """Test APRS protocol initialization"""
        assert aprs_protocol.name == 'aprs_test'
        assert aprs_protocol.server == 'test.aprs.net'
        assert aprs_protocol.port == 14580
        assert aprs_protocol.callsign == 'W4TEST'
        assert aprs_protocol.passcode == '12345'
        assert aprs_protocol.message_prefix == 'RARSMS'
        assert aprs_protocol.require_prefix is True
        assert 'W4ABC' in aprs_protocol.authorized_callsigns
        assert not aprs_protocol.is_connected

    def test_get_capabilities(self, aprs_protocol):
        """Test APRS protocol capabilities"""
        caps = aprs_protocol.get_capabilities()

        assert isinstance(caps, ProtocolCapabilities)
        assert caps.can_send is True
        assert caps.can_receive is True
        assert caps.supports_position is True
        assert caps.supports_threading is False
        assert caps.supports_attachments is False
        assert caps.max_message_length == 67

    def test_is_configured_valid(self, aprs_protocol):
        """Test is_configured with valid configuration"""
        assert aprs_protocol.is_configured() is True

    def test_is_configured_missing_callsign(self):
        """Test is_configured with missing callsign"""
        config = {
            'aprs_passcode': '12345'
        }
        protocol = APRSProtocol('test', config)
        assert protocol.is_configured() is False

    def test_is_configured_missing_passcode(self):
        """Test is_configured with missing passcode"""
        config = {
            'aprs_callsign': 'W4TEST'
        }
        protocol = APRSProtocol('test', config)
        assert protocol.is_configured() is False

    def test_parse_position_message(self, aprs_protocol):
        """Test parsing APRS position messages"""
        # Standard position packet
        packet = "W4ABC-9>APRS,TCPIP*:!3547.12N/07838.45W>Mobile station"
        message = aprs_protocol.parse_incoming_message(packet)

        assert message is not None
        assert message.source_protocol == 'aprs_test'
        assert message.source_id == 'W4ABC-9'
        assert message.message_type == MessageType.POSITION
        assert 'Position update' in message.content
        assert 'position' in message.metadata

        # Check position data
        position = message.metadata['position']
        assert abs(position['lat'] - 35.7853) < 0.01  # 35°47.12'N
        assert abs(position['lon'] - (-78.6408)) < 0.01  # 078°38.45'W

    def test_parse_position_with_timestamp(self, aprs_protocol):
        """Test parsing position messages with timestamp"""
        packet = "W4ABC>APRS,TCPIP*:@092345z3547.12N/07838.45W>Station with timestamp"
        message = aprs_protocol.parse_incoming_message(packet)

        assert message is not None
        assert message.message_type == MessageType.POSITION
        assert 'position' in message.metadata

    def test_parse_text_message_addressed_to_rarsms(self, aprs_protocol):
        """Test parsing text message addressed to RARSMS"""
        packet = "W4ABC>APRS,TCPIP*::RARSMS   :Hello from the field!"
        message = aprs_protocol.parse_incoming_message(packet)

        assert message is not None
        assert message.source_id == 'W4ABC'
        assert message.message_type == MessageType.TEXT
        assert message.content == 'Hello from the field!'
        assert message.metadata['addressee'] == 'RARSMS'
        assert message.metadata['addressed_to_rarsms'] is True
        assert message.metadata['has_rarsms_prefix'] is False

    def test_parse_text_message_with_rarsms_prefix(self, aprs_protocol):
        """Test parsing text message with RARSMS prefix"""
        packet = "KJ4XYZ>APRS,TCPIP*::CQ      :RARSMS: Anyone on frequency?"
        message = aprs_protocol.parse_incoming_message(packet)

        assert message is not None
        assert message.source_id == 'KJ4XYZ'
        assert message.message_type == MessageType.TEXT
        assert message.content == 'Anyone on frequency?'  # Prefix removed
        assert message.metadata['addressee'] == 'CQ'
        assert message.metadata['addressed_to_rarsms'] is False
        assert message.metadata['has_rarsms_prefix'] is True

    def test_parse_text_message_with_msg_number(self, aprs_protocol):
        """Test parsing text message with message number"""
        packet = "W4ABC>APRS,TCPIP*::RARSMS   :Test message{123}"
        message = aprs_protocol.parse_incoming_message(packet)

        assert message is not None
        assert message.content == 'Test message'
        assert message.metadata['msg_no'] == '123'

    def test_parse_invalid_packets(self, aprs_protocol):
        """Test parsing invalid APRS packets"""
        invalid_packets = [
            "InvalidPacketNoColon",
            "NoGreaterThan:data",
            "",
            "W4ABC>APRS,TCPIP*:",  # Empty data
        ]

        for packet in invalid_packets:
            message = aprs_protocol.parse_incoming_message(packet)
            assert message is None

    def test_authorization_check(self, aprs_protocol):
        """Test callsign authorization"""
        # Authorized callsigns
        assert aprs_protocol._is_authorized('W4ABC') is True
        assert aprs_protocol._is_authorized('W4ABC-9') is True  # SSID stripped
        assert aprs_protocol._is_authorized('KJ4XYZ') is True
        assert aprs_protocol._is_authorized('N4DEF-15') is True

        # Unauthorized callsigns
        assert aprs_protocol._is_authorized('W4XYZ') is False
        assert aprs_protocol._is_authorized('VE3ABC') is False

    def test_authorization_empty_list(self):
        """Test authorization with empty list (allow all)"""
        config = {
            'aprs_callsign': 'W4TEST',
            'aprs_passcode': '12345',
            'authorized_callsigns': []
        }
        protocol = APRSProtocol('test', config)

        # Should allow all when no filter
        assert protocol._is_authorized('W4ABC') is True
        assert protocol._is_authorized('VE3XYZ') is True

    def test_message_routing_rules_prefix_required(self, aprs_protocol):
        """Test message routing with prefix requirement"""
        # Position messages should always be routed
        pos_message = Message(
            source_protocol='aprs_test',
            source_id='W4ABC',
            message_type=MessageType.POSITION,
            content='Position update'
        )
        assert aprs_protocol._should_route_message(pos_message) is True

        # Text message addressed to RARSMS should be routed
        rarsms_message = Message(
            source_protocol='aprs_test',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Hello',
            metadata={'addressed_to_rarsms': True, 'has_rarsms_prefix': False}
        )
        assert aprs_protocol._should_route_message(rarsms_message) is True

        # Text message with RARSMS prefix should be routed
        prefix_message = Message(
            source_protocol='aprs_test',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Hello',
            metadata={'addressed_to_rarsms': False, 'has_rarsms_prefix': True}
        )
        assert aprs_protocol._should_route_message(prefix_message) is True

        # Text message without prefix should NOT be routed
        no_prefix_message = Message(
            source_protocol='aprs_test',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Hello',
            metadata={'addressed_to_rarsms': False, 'has_rarsms_prefix': False}
        )
        assert aprs_protocol._should_route_message(no_prefix_message) is False

    def test_message_routing_rules_prefix_not_required(self):
        """Test message routing without prefix requirement"""
        config = {
            'aprs_callsign': 'W4TEST',
            'aprs_passcode': '12345',
            'require_prefix': False
        }
        protocol = APRSProtocol('test', config)

        # All messages should be routed when prefix not required
        any_message = Message(
            source_protocol='test',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Any message',
            metadata={'addressed_to_rarsms': False, 'has_rarsms_prefix': False}
        )
        assert protocol._should_route_message(any_message) is True

    def test_format_message_packet(self, aprs_protocol):
        """Test formatting APRS message packets"""
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Hello W4ABC!'
        )

        with patch('time.time', return_value=1234567890):
            packet = aprs_protocol._format_message_packet(message, 'W4ABC')
            # Should include properly padded addressee and message number
            assert packet.startswith(':W4ABC    :Hello W4ABC!{')
            assert packet.endswith('890')  # Last 3 digits of timestamp

    def test_format_message_packet_truncation(self, aprs_protocol):
        """Test message packet truncation for length limit"""
        long_content = 'A' * 100  # Too long for APRS
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content=long_content
        )

        with patch('time.time', return_value=1234567890):
            packet = aprs_protocol._format_message_packet(message, 'W4ABC')
            # Should be truncated with "..." but still include message number
            assert len(packet) <= 67
            assert '...' in packet
            assert packet.endswith('{890')

    def test_format_position_packet(self, aprs_protocol):
        """Test formatting APRS position packets"""
        message = Message(
            source_protocol='test',
            source_id='W4ABC',
            message_type=MessageType.POSITION,
            content='Mobile station',
            metadata={
                'position': {'lat': 35.7796, 'lon': -78.6382}
            }
        )

        packet = aprs_protocol._format_position_packet(message)
        # Should contain position in APRS format
        assert packet.startswith('!')
        assert 'N/' in packet  # North latitude
        assert 'W>' in packet  # West longitude
        assert 'Mobile station' in packet

    def test_format_position_packet_no_position(self, aprs_protocol):
        """Test formatting position packet without position data"""
        message = Message(
            source_protocol='test',
            source_id='W4ABC',
            message_type=MessageType.POSITION,
            content='Status update'
        )

        packet = aprs_protocol._format_position_packet(message)
        assert packet == '>Status update'

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, aprs_protocol):
        """Test sending message when not connected"""
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        result = await aprs_protocol.send_message(message)
        assert result is False

    def test_parse_position_coordinates(self, aprs_protocol):
        """Test parsing various coordinate formats"""
        test_cases = [
            # Format: !DDMM.mmN/DDDMM.mmW
            ("!3547.12N/07838.45W>", 35.7853, -78.6408),
            ("!3500.00N/07800.00W>", 35.0, -78.0),
            ("!3559.99S/07859.99E>", -35.9998, 78.9998),
        ]

        for pos_data, expected_lat, expected_lon in test_cases:
            position = aprs_protocol._parse_position(pos_data)
            assert position is not None
            assert abs(position['lat'] - expected_lat) < 0.01
            assert abs(position['lon'] - expected_lon) < 0.01

    def test_parse_position_invalid_formats(self, aprs_protocol):
        """Test parsing invalid position formats"""
        invalid_positions = [
            "!invalid",
            "!3547.12X/07838.45W>",  # Invalid latitude direction
            "!3547.12N/07838.45Z>",  # Invalid longitude direction
            "!35N/078W>",            # Too short
            "",
        ]

        for pos_data in invalid_positions:
            position = aprs_protocol._parse_position(pos_data)
            assert position is None

    def test_parse_message_formats(self, aprs_protocol):
        """Test parsing various message formats"""
        test_cases = [
            (":CQ      :General message", "CQ", "General message", None),
            (":W4ABC   :Direct message{123}", "W4ABC", "Direct message", "123"),
            (":RARSMS  :Test message", "RARSMS", "Test message", None),
        ]

        for msg_data, expected_addr, expected_msg, expected_no in test_cases:
            result = aprs_protocol._parse_message(msg_data)
            assert result is not None
            assert result['addressee'] == expected_addr
            assert result['message'] == expected_msg
            assert result['msg_no'] == expected_no

    def test_parse_message_invalid_formats(self, aprs_protocol):
        """Test parsing invalid message formats"""
        invalid_messages = [
            "NoColonAtStart",
            ":NoSecondColon",
            "",
        ]

        for msg_data in invalid_messages:
            result = aprs_protocol._parse_message(msg_data)
            assert result is None

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, aprs_protocol):
        """Test proper cleanup during disconnect"""
        # Setup some state
        aprs_protocol.is_connected = True
        aprs_protocol.socket = Mock()
        aprs_protocol.socket.close = Mock()

        # Create a real async task that can be cancelled
        async def dummy_task():
            await asyncio.sleep(10)

        task = asyncio.create_task(dummy_task())
        aprs_protocol.reader_task = task

        result = await aprs_protocol.disconnect()

        assert result is True
        assert aprs_protocol.is_connected is False
        assert aprs_protocol.socket is None
        assert aprs_protocol.reader_task is None

    def test_integration_full_message_flow(self, aprs_protocol):
        """Test complete message parsing flow"""
        # Test a complete APRS packet flow
        test_packet = "W4ABC-9>APRS,TCPIP*::RARSMS   :Emergency at I-40 mile marker 123{456}"

        # Parse the message
        message = aprs_protocol.parse_incoming_message(test_packet)

        # Verify parsing
        assert message is not None
        assert message.source_id == 'W4ABC-9'
        assert message.message_type == MessageType.TEXT
        assert message.content == 'Emergency at I-40 mile marker 123'
        assert message.metadata['addressee'] == 'RARSMS'
        assert message.metadata['msg_no'] == '456'
        assert message.metadata['addressed_to_rarsms'] is True

        # Check authorization
        assert aprs_protocol._is_authorized(message.source_id) is True

        # Check routing decision
        assert aprs_protocol._should_route_message(message) is True

    def test_callsign_case_consistency(self, aprs_protocol):
        """Test that callsigns are converted to uppercase"""
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        # Test lowercase callsign gets converted to uppercase
        with patch('time.time', return_value=1234567890):
            packet = aprs_protocol._format_message_packet(message, 'kk4pwj-10')
            assert packet.startswith(':KK4PWJ-10:')  # Should be uppercase

    def test_message_format_compliance(self, aprs_protocol):
        """Test APRS message format compliance with specification"""
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Testing message format'
        )

        with patch('time.time', return_value=1234567890):
            packet = aprs_protocol._format_message_packet(message, 'W4ABC')

            # Check format: :ADDRESSEE :message{MSGNO}
            parts = packet.split(':')
            assert len(parts) == 3  # Should have 3 parts separated by colons
            assert parts[0] == ''  # First part should be empty (starts with colon)
            assert len(parts[1]) == 9  # Addressee should be exactly 9 characters
            assert parts[1] == 'W4ABC    '  # Should be padded with spaces
            assert parts[2].endswith('{890')  # Should end with message number

    def test_message_number_generation(self, aprs_protocol):
        """Test message number generation"""
        message = Message(
            source_protocol='test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Test'
        )

        # Test with different timestamps
        with patch('time.time', return_value=1234567123):
            packet1 = aprs_protocol._format_message_packet(message, 'W4ABC')
            assert packet1.endswith('{123')

        with patch('time.time', return_value=1234567456):
            packet2 = aprs_protocol._format_message_packet(message, 'W4ABC')
            assert packet2.endswith('{456')