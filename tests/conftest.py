#!/usr/bin/env python3

import pytest
import tempfile
import os
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing"""
    config_content = """
# Test configuration
aprs_server: "test.aprs.net"
aprs_port: 14580
aprs_callsign: "TEST-1"
aprs_passcode: "12345"
filter_lat: "35.7796"
filter_lon: "-78.6382"
filter_distance: "100"
message_prefix: "RARSMS"
require_prefix: true

protocols:
  discord_test:
    enabled: true
    type: "discord_bot"
    discord_bot_token: "test_token"
    discord_channel_id: "123456789"
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name

    # Cleanup
    os.unlink(f.name)

@pytest.fixture
def temp_callsigns_file():
    """Create a temporary callsigns file for testing"""
    callsigns_content = """# Test callsigns
TEST-1
TEST-2
W4ABC
# Comment line
KJ4XYZ
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(callsigns_content)
        f.flush()
        yield f.name

    # Cleanup
    os.unlink(f.name)

@pytest.fixture
def mock_discord_bot():
    """Create a mock Discord bot for testing"""
    bot = AsyncMock()
    bot.user = Mock()
    bot.user.id = 123456789
    bot.user.name = "TestBot"
    bot.is_ready.return_value = True

    # Mock channel
    channel = AsyncMock()
    channel.id = 123456789
    channel.name = "test-channel"
    channel.send = AsyncMock()

    bot.get_channel.return_value = channel

    return bot

@pytest.fixture
def mock_discord_message():
    """Create a mock Discord message for testing"""
    message = Mock()
    message.id = 987654321
    message.content = "Test message content"
    message.author = Mock()
    message.author.id = 111111111
    message.author.display_name = "TestUser"
    message.author.discriminator = "1234"
    message.channel = Mock()
    message.channel.id = 123456789
    message.reference = None
    message.add_reaction = AsyncMock()

    return message

@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'aprs_server': 'test.aprs.net',
        'aprs_port': 14580,
        'aprs_callsign': 'TEST-1',
        'aprs_passcode': '12345',
        'filter_lat': '35.7796',
        'filter_lon': '-78.6382',
        'filter_distance': '100',
        'message_prefix': 'RARSMS',
        'require_prefix': True,
        'discord_bot_token': 'test_token',
        'discord_channel_id': '123456789',
        'authorized_callsigns': ['TEST-1', 'TEST-2', 'W4ABC']
    }

@pytest.fixture
def mock_protocol_callback():
    """Mock protocol callback function"""
    return Mock()