#!/usr/bin/env python3

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from main import RARSMSBridge

class TestIntegration:
    """Integration tests for the complete RARSMS system"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configuration_loading_integration(self):
        """Test that configuration loading works end-to-end"""
        config_content = """
aprs_server: "test.aprs.net"
aprs_port: 14580
aprs_callsign: "W4TEST"
aprs_passcode: "12345"
discord_bot_token: "test_bot_token"
discord_channel_id: "123456789"
message_prefix: "RARSMS"
require_prefix: true

protocols:
  discord_secondary:
    enabled: true
    type: "discord_bot"
    discord_bot_token: "secondary_token"
    discord_channel_id: "987654321"

routing:
  text_bridging:
    enabled: true
    source_protocols: ["aprs_main"]
    target_protocols: ["discord_main", "discord_secondary"]
    message_types: ["text"]
    bidirectional: true
"""

        callsigns_content = """# Test callsigns
W4TEST
W4ABC
KJ4XYZ
"""

        with patch('os.path.exists') as mock_exists:
            def exists_side_effect(path):
                return path in ['config.yaml', 'callsigns.txt']
            mock_exists.side_effect = exists_side_effect

            with patch('builtins.open', side_effect=[
                mock_open(read_data=config_content).return_value,
                mock_open(read_data=callsigns_content).return_value
            ]):
                bridge = RARSMSBridge()

                # Test configuration was loaded correctly
                assert bridge.config['aprs_callsign'] == 'W4TEST'
                assert bridge.config['aprs_passcode'] == '12345'
                assert bridge.config['discord_bot_token'] == 'test_bot_token'
                assert bridge.config['discord_channel_id'] == '123456789'

                # Test authorized callsigns
                assert 'W4TEST' in bridge.config['authorized_callsigns']
                assert 'W4ABC' in bridge.config['authorized_callsigns']
                assert 'KJ4XYZ' in bridge.config['authorized_callsigns']

    @pytest.mark.integration
    def test_protocol_setup_aprs_only(self):
        """Test protocol setup with APRS only"""
        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                # Should have APRS protocol
                assert 'aprs_main' in bridge.protocol_manager.protocols

                # Should not have Discord protocol
                assert 'discord_main' not in bridge.protocol_manager.protocols

    @pytest.mark.integration
    @pytest.mark.skip(reason="Discord webhook integration test deprecated - project uses Discord bot approach")
    def test_protocol_setup_discord_webhook_only(self):
        """Test protocol setup with Discord webhook only"""
        pass

    @pytest.mark.integration
    def test_protocol_setup_discord_bot_only(self):
        """Test protocol setup with Discord bot only"""
        with patch.dict(os.environ, {
            'DISCORD_BOT_TOKEN': 'test_bot_token',
            'DISCORD_CHANNEL_ID': '123456789'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                # Should have Discord bot protocol
                assert 'discord_main' in bridge.protocol_manager.protocols

                # Check it's the bot type
                protocol = bridge.protocol_manager.protocols['discord_main']
                assert hasattr(protocol, 'bot_token')

    @pytest.mark.integration
    def test_protocol_setup_both_aprs_and_discord(self):
        """Test protocol setup with both APRS and Discord"""
        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345',
            'DISCORD_BOT_TOKEN': 'test_bot_token',
            'DISCORD_CHANNEL_ID': '123456789'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                # Should have both protocols
                assert 'aprs_main' in bridge.protocol_manager.protocols
                assert 'discord_main' in bridge.protocol_manager.protocols

    @pytest.mark.integration
    def test_routing_rules_setup(self):
        """Test that routing rules are set up correctly"""
        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345',
            'DISCORD_BOT_TOKEN': 'test_bot_token',
            'DISCORD_CHANNEL_ID': '123456789'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()
                bridge.setup_routing_rules()

                rules = bridge.protocol_manager.get_routing_rules()

                # Should have default bidirectional rule
                assert len(rules) >= 2  # Bidirectional creates two rules

                # Check for APRS -> Discord rule
                aprs_to_discord = any(
                    rule for rule in rules
                    if 'aprs_main' in rule['source_protocols'] and
                       'discord_main' in rule['target_protocols']
                )
                assert aprs_to_discord

    @pytest.mark.integration
    def test_no_protocols_configured_graceful_shutdown(self):
        """Test graceful shutdown when no protocols are configured"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                # Should have no protocols
                status = bridge.protocol_manager.get_protocol_status()
                assert len(status) == 0

    @pytest.mark.integration
    def test_invalid_discord_webhook_url_handling(self):
        """Test handling of invalid Discord webhook URL"""
        with patch.dict(os.environ, {
            'DISCORD_WEBHOOK_URL': 'not_a_valid_webhook_url'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                # Should not create Discord protocol with invalid URL
                assert 'discord_main' not in bridge.protocol_manager.protocols

    @pytest.mark.integration
    def test_configuration_yaml_override_environment(self):
        """Test that YAML configuration works when environment variables are present"""
        config_content = """
aprs_callsign: "YAML-CALL"
aprs_passcode: "99999"
discord_bot_token: "yaml_bot_token"
discord_channel_id: "yaml_channel_id"
"""

        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'ENV-CALL',
            'APRS_PASSCODE': '11111'
        }, clear=True):
            with patch('os.path.exists') as mock_exists:
                def exists_side_effect(path):
                    return path == 'config.yaml'
                mock_exists.side_effect = exists_side_effect

                with patch('builtins.open', mock_open(read_data=config_content)):
                    bridge = RARSMSBridge()

                    # Environment should override YAML
                    assert bridge.config['aprs_callsign'] == 'ENV-CALL'
                    assert bridge.config['aprs_passcode'] == '11111'

                    # YAML should provide values not in environment
                    assert bridge.config['discord_bot_token'] == 'yaml_bot_token'
                    assert bridge.config['discord_channel_id'] == 'yaml_channel_id'

    @pytest.mark.integration
    def test_environment_variables_boolean_parsing(self):
        """Test that boolean environment variables are parsed correctly"""
        test_cases = [
            ('true', True),
            ('false', False),
            ('True', True),
            ('False', False),
            ('TRUE', True),
            ('FALSE', False)
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {
                'REQUIRE_PREFIX': env_value
            }, clear=True):
                with patch('os.path.exists', return_value=False):
                    bridge = RARSMSBridge()
                    assert bridge.config['require_prefix'] == expected

    @pytest.mark.integration
    def test_protocol_capabilities_retrieval(self):
        """Test that protocol capabilities can be retrieved"""
        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345',
            'DISCORD_BOT_TOKEN': 'test_bot_token',
            'DISCORD_CHANNEL_ID': '123456789'
        }, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()
                bridge.setup_protocols()

                status = bridge.protocol_manager.get_protocol_status()

                # Check APRS capabilities
                if 'aprs_main' in bridge.protocol_manager.protocols:
                    aprs_protocol = bridge.protocol_manager.protocols['aprs_main']
                    caps = aprs_protocol.get_capabilities()

                    assert caps.can_send is True
                    assert caps.can_receive is True
                    assert caps.supports_position is True
                    assert caps.max_message_length == 67

                # Check Discord capabilities
                if 'discord_main' in bridge.protocol_manager.protocols:
                    discord_protocol = bridge.protocol_manager.protocols['discord_main']
                    caps = discord_protocol.get_capabilities()

                    assert caps.can_send is True
                    assert caps.can_receive is True
                    assert caps.supports_position is True
                    assert caps.max_message_length == 2000

    @pytest.mark.integration
    def test_authorization_system_integration(self):
        """Test that the authorization system works across the bridge"""
        callsigns_content = """W4TEST
W4ABC
# Comment line
KJ4XYZ

"""

        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345'
        }, clear=True):
            with patch('os.path.exists') as mock_exists:
                def exists_side_effect(path):
                    return path == 'callsigns.txt'
                mock_exists.side_effect = exists_side_effect

                with patch('builtins.open', mock_open(read_data=callsigns_content)):
                    bridge = RARSMSBridge()
                    bridge.setup_protocols()

                    # Check that authorized callsigns were loaded
                    callsigns = bridge.config['authorized_callsigns']
                    assert 'W4TEST' in callsigns
                    assert 'W4ABC' in callsigns
                    assert 'KJ4XYZ' in callsigns
                    assert len(callsigns) == 3  # Comments should be filtered out

                    # Check that APRS protocol has the same callsigns
                    if 'aprs_main' in bridge.protocol_manager.protocols:
                        aprs_protocol = bridge.protocol_manager.protocols['aprs_main']
                        assert 'W4TEST' in aprs_protocol.authorized_callsigns
                        assert 'W4ABC' in aprs_protocol.authorized_callsigns
                        assert 'KJ4XYZ' in aprs_protocol.authorized_callsigns