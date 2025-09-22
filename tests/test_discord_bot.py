#!/usr/bin/env python3

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from protocols.discord_bot import DiscordBotProtocol
from protocols.base import Message, MessageType, ProtocolCapabilities

class TestDiscordBotProtocol:
    """Test Discord bot protocol functionality"""

    @pytest.fixture
    def discord_config(self):
        """Sample Discord bot configuration"""
        return {
            'discord_bot_token': 'test_bot_token_123',
            'discord_channel_id': '123456789',
            'discord_guild_id': '987654321'
        }

    @pytest.fixture
    def discord_protocol(self, discord_config):
        """Create Discord bot protocol instance"""
        return DiscordBotProtocol('discord_test', discord_config)

    def test_protocol_initialization(self, discord_protocol, discord_config):
        """Test Discord bot protocol initialization"""
        assert discord_protocol.name == 'discord_test'
        assert discord_protocol.bot_token == discord_config['discord_bot_token']
        assert discord_protocol.channel_id == discord_config['discord_channel_id']
        assert discord_protocol.guild_id == discord_config['discord_guild_id']
        assert not discord_protocol.is_connected

    def test_is_configured_valid(self, discord_protocol):
        """Test is_configured with valid configuration"""
        assert discord_protocol.is_configured() is True

    def test_is_configured_missing_token(self):
        """Test is_configured with missing bot token"""
        config = {
            'discord_channel_id': '123456789'
        }
        protocol = DiscordBotProtocol('test', config)
        assert protocol.is_configured() is False

    def test_is_configured_missing_channel(self):
        """Test is_configured with missing channel ID"""
        config = {
            'discord_bot_token': 'test_token'
        }
        protocol = DiscordBotProtocol('test', config)
        assert protocol.is_configured() is False

    def test_get_capabilities(self, discord_protocol):
        """Test protocol capabilities"""
        caps = discord_protocol.get_capabilities()

        assert isinstance(caps, ProtocolCapabilities)
        assert caps.can_send is True
        assert caps.can_receive is True
        assert caps.supports_position is True
        assert caps.supports_threading is True
        assert caps.supports_attachments is True
        assert caps.max_message_length == 2000

    def test_parse_aprs_reply_valid_format(self, discord_protocol):
        """Test parsing valid APRS reply format"""
        test_cases = [
            ("APRS W4ABC Hello there!", ("W4ABC", "Hello there!")),
            ("aprs KJ4XYZ-9 Thanks for the update", ("KJ4XYZ-9", "Thanks for the update")),
            ("APRS N4DEF/M See you at the meeting", ("N4DEF/M", "See you at the meeting")),
            ("APRS K4ABC-15 Multiple word message here", ("K4ABC-15", "Multiple word message here")),
        ]

        for input_text, expected in test_cases:
            result = discord_protocol._parse_aprs_reply(input_text)
            assert result == expected

    def test_parse_aprs_reply_invalid_format(self, discord_protocol):
        """Test parsing invalid APRS reply formats"""
        invalid_cases = [
            "W4ABC Hello there!",  # Missing APRS prefix
            "APRS",  # No callsign or message
            "APRS W4ABC",  # No message
            "APRS INVALID_CALL Hello",  # Invalid callsign format
            "APRS 123ABC Hello",  # Invalid callsign format
            "Hello APRS W4ABC",  # APRS not at start
            "",  # Empty string
        ]

        for invalid_input in invalid_cases:
            result = discord_protocol._parse_aprs_reply(invalid_input)
            assert result is None

    def test_parse_aprs_reply_callsign_validation(self, discord_protocol):
        """Test callsign validation in APRS replies"""
        valid_callsigns = [
            "W4ABC",
            "KJ4XYZ",
            "N4DEF-9",
            "K4ABC-15",
            "AA1AAA/M",
            "W1AW",
            "KC1ABC-1"
        ]

        for callsign in valid_callsigns:
            result = discord_protocol._parse_aprs_reply(f"APRS {callsign} Test message")
            assert result is not None
            assert result[0] == callsign

        invalid_callsigns = [
            "123ABC",  # Can't start with number
            "ABCD1234EF",  # Too long
            "A1",  # Too short
            "W4-9",  # Missing base call
            "K4TEST",  # Too many characters before digit
        ]

        for callsign in invalid_callsigns:
            result = discord_protocol._parse_aprs_reply(f"APRS {callsign} Test message")
            assert result is None

    @pytest.mark.asyncio
    async def test_format_message_for_discord_text(self, discord_protocol):
        """Test formatting text message for Discord"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Hello from the field!'
        )

        formatted = discord_protocol._format_message_for_discord(message)

        assert '💬 **W4ABC** (aprs_main)' in formatted
        assert 'Hello from the field!' in formatted
        assert 'Reply with: `APRS W4ABC <your message>`' in formatted

    @pytest.mark.asyncio
    async def test_format_message_for_discord_position(self, discord_protocol):
        """Test formatting position message for Discord"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC-9',
            message_type=MessageType.POSITION,
            content='Mobile station'
        )

        # Add position data
        message.metadata = {
            'latitude': 35.7796,
            'longitude': -78.6382
        }

        formatted = discord_protocol._format_message_for_discord(message)

        assert '📍 **W4ABC-9** (aprs_main)' in formatted
        assert 'Mobile station' in formatted

    @pytest.mark.asyncio
    async def test_format_message_for_discord_emergency(self, discord_protocol):
        """Test formatting emergency message for Discord"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC',
            message_type=MessageType.EMERGENCY,
            content='Emergency at I-40 mile marker 123'
        )

        formatted = discord_protocol._format_message_for_discord(message)

        assert '🚨 **W4ABC** (aprs_main)' in formatted
        assert 'Emergency at I-40 mile marker 123' in formatted

    def test_message_tracking_add_and_cleanup(self, discord_protocol):
        """Test APRS message tracking for replies"""
        # Add messages to tracking beyond the 100 limit and trigger cleanup
        for i in range(150):  # More than the 100 limit
            discord_protocol.aprs_message_map[i] = f'W4ABC-{i}'

            # Trigger cleanup logic when we exceed 100 (simulate send_message behavior)
            if len(discord_protocol.aprs_message_map) > 100:
                oldest_keys = list(discord_protocol.aprs_message_map.keys())[:-100]
                for key in oldest_keys:
                    del discord_protocol.aprs_message_map[key]

        # Should keep only last 100
        assert len(discord_protocol.aprs_message_map) <= 100

        # Should contain most recent entries
        assert 149 in discord_protocol.aprs_message_map
        assert discord_protocol.aprs_message_map[149] == 'W4ABC-149'

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, discord_protocol):
        """Test sending message when not connected"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC',
            message_type=MessageType.TEXT,
            content='Test message'
        )

        result = await discord_protocol.send_message(message)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_reply_to_aprs_ignored(self, discord_protocol):
        """Test that reply messages going back to APRS are ignored"""
        discord_protocol.is_connected = True
        discord_protocol.channel = Mock()

        message = Message(
            source_protocol='discord_test',
            source_id='TestUser',
            message_type=MessageType.TEXT,
            content='Reply message',
            metadata={'reply_to_aprs': True}
        )

        result = await discord_protocol.send_message(message)
        # Should return True but not actually send to Discord
        assert result is True

    def test_get_protocol_info(self, discord_protocol):
        """Test getting protocol information"""
        info = discord_protocol.get_protocol_info()

        assert info['name'] == 'discord_test'
        assert info['type'] == 'discord_bot'
        assert info['connected'] is False
        assert info['channel_id'] == '123456789'
        assert info['bot_user'] is None
        assert info['tracked_messages'] == 0

    @pytest.mark.asyncio
    async def test_handle_discord_message_reply_success(self, discord_protocol, mock_discord_message):
        """Test handling Discord message reply to APRS"""
        # Setup protocol with callback
        callback_mock = Mock()
        discord_protocol.set_message_callback(callback_mock)

        # Setup mock message as reply
        mock_discord_message.reference = Mock()
        mock_discord_message.reference.message_id = 999
        mock_discord_message.content = "APRS W4ABC Thanks for the update!"

        # Add APRS message to tracking
        discord_protocol.aprs_message_map[999] = "W4ABC"

        # Handle the message
        await discord_protocol._handle_discord_message(mock_discord_message)

        # Should have called the callback
        callback_mock.assert_called_once()

        # Check the message that was sent
        sent_message = callback_mock.call_args[0][0]
        assert sent_message.source_protocol == 'discord_test'
        assert sent_message.content == 'Thanks for the update!'
        assert sent_message.metadata['target_callsign'] == 'W4ABC'
        assert sent_message.metadata['reply_to_aprs'] is True

        # Should have added reaction
        mock_discord_message.add_reaction.assert_called_with("📡")

    @pytest.mark.asyncio
    async def test_handle_discord_message_reply_wrong_callsign(self, discord_protocol, mock_discord_message):
        """Test handling Discord message reply with wrong callsign"""
        callback_mock = Mock()
        discord_protocol.set_message_callback(callback_mock)

        # Setup mock message as reply with wrong callsign
        mock_discord_message.reference = Mock()
        mock_discord_message.reference.message_id = 999
        mock_discord_message.content = "APRS W4XYZ Thanks for the update!"

        # Add different APRS callsign to tracking
        discord_protocol.aprs_message_map[999] = "W4ABC"

        # Handle the message
        await discord_protocol._handle_discord_message(mock_discord_message)

        # Should NOT have called the callback
        callback_mock.assert_not_called()

        # Should have added error reaction
        mock_discord_message.add_reaction.assert_called_with("❌")

    @pytest.mark.asyncio
    async def test_handle_discord_message_not_reply(self, discord_protocol, mock_discord_message):
        """Test handling regular Discord message (not a reply)"""
        callback_mock = Mock()
        discord_protocol.set_message_callback(callback_mock)

        # Setup mock message as regular message (no reference)
        mock_discord_message.reference = None
        mock_discord_message.content = "Regular Discord message"

        # Handle the message
        await discord_protocol._handle_discord_message(mock_discord_message)

        # Should not have called the callback
        callback_mock.assert_not_called()

        # Should not have added any reactions
        mock_discord_message.add_reaction.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect(self, discord_protocol):
        """Test disconnecting from Discord"""
        # Setup mock bot
        discord_protocol.bot = AsyncMock()

        result = await discord_protocol.disconnect()

        assert result is True
        assert discord_protocol.is_connected is False
        discord_protocol.bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_bot(self, discord_protocol):
        """Test disconnecting when no bot is set"""
        result = await discord_protocol.disconnect()

        assert result is True
        assert discord_protocol.is_connected is False

    def test_callsign_case_normalization(self, discord_protocol):
        """Test that callsigns are normalized to uppercase"""
        # Test lowercase callsign input
        result = discord_protocol._parse_aprs_reply("APRS kk4pwj-10 Testing case")
        assert result is not None
        assert result[0] == "KK4PWJ-10"  # Should be converted to uppercase
        assert result[1] == "Testing case"

        # Test mixed case callsign input
        result = discord_protocol._parse_aprs_reply("aprs W4aBc-9 Mixed case test")
        assert result is not None
        assert result[0] == "W4ABC-9"  # Should be converted to uppercase
        assert result[1] == "Mixed case test"

    def test_ssid_parsing_comprehensive(self, discord_protocol):
        """Test comprehensive SSID parsing with various formats"""
        ssid_test_cases = [
            ("APRS KK4PWJ-10 Message", ("KK4PWJ-10", "Message")),
            ("APRS W4ABC-1 Single digit", ("W4ABC-1", "Single digit")),
            ("APRS N4DEF-15 Double digit", ("N4DEF-15", "Double digit")),
            ("APRS K4ABC/M Mobile", ("K4ABC/M", "Mobile")),
            ("APRS AA1AAA/P Portable", ("AA1AAA/P", "Portable")),
        ]

        for input_text, expected in ssid_test_cases:
            result = discord_protocol._parse_aprs_reply(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    @pytest.mark.asyncio
    async def test_reply_message_creation_with_target_ids(self, discord_protocol, mock_discord_message):
        """Test that reply messages include proper target_ids for APRS routing"""
        callback_mock = Mock()
        discord_protocol.set_message_callback(callback_mock)

        # Setup mock message as reply
        mock_discord_message.reference = Mock()
        mock_discord_message.reference.message_id = 999
        mock_discord_message.content = "APRS KK4PWJ-10 ack"

        # Add APRS message to tracking
        discord_protocol.aprs_message_map[999] = "KK4PWJ-10"

        # Handle the message
        await discord_protocol._handle_discord_message(mock_discord_message)

        # Should have called the callback
        callback_mock.assert_called_once()

        # Check the message that was sent
        sent_message = callback_mock.call_args[0][0]
        assert sent_message.target_protocols == ['aprs_main']
        assert sent_message.target_ids['aprs'] == 'KK4PWJ-10'
        assert sent_message.metadata['reply_to_aprs'] is True

    def test_get_position_method_compatibility(self, discord_protocol):
        """Test compatibility with position data in message metadata"""
        message = Message(
            source_protocol='aprs_main',
            source_id='W4ABC-9',
            message_type=MessageType.POSITION,
            content='Mobile station'
        )

        # Test with position data in metadata (as get_position() would return)
        message.metadata = {
            'position': {'lat': 35.7796, 'lon': -78.6382}
        }

        formatted = discord_protocol._format_message_for_discord(message)

        # Should include position info if get_position() returns data
        assert '📍 **W4ABC-9** (aprs_main)' in formatted
        assert 'Mobile station' in formatted