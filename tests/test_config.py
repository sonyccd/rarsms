#!/usr/bin/env python3

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, mock_open
from main import RARSMSBridge

class TestConfigurationLoading:
    """Test configuration loading functionality"""

    def test_load_config_from_environment_only(self):
        """Test loading configuration from environment variables only"""
        env_vars = {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '54321',
            'APRS_SERVER': 'env.aprs.net',
            'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/test',
            'MESSAGE_PREFIX': 'ENVTEST'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('os.path.exists', return_value=False):  # No config.yaml
                bridge = RARSMSBridge()
                config = bridge.config

                assert config['aprs_callsign'] == 'W4TEST'
                assert config['aprs_passcode'] == '54321'
                assert config['aprs_server'] == 'env.aprs.net'
                assert config['discord_webhook_url'] == 'https://discord.com/api/webhooks/test'
                assert config['message_prefix'] == 'ENVTEST'

    def test_load_config_from_yaml_only(self, temp_config_file):
        """Test loading configuration from YAML file only"""
        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            with patch('os.path.exists') as mock_exists:
                def exists_side_effect(path):
                    return path == 'config.yaml'
                mock_exists.side_effect = exists_side_effect

                with patch('builtins.open', mock_open(read_data="""
aprs_callsign: "YAML-1"
aprs_passcode: "99999"
aprs_server: "yaml.aprs.net"
message_prefix: "YAMLTEST"
""")):
                    bridge = RARSMSBridge()
                    config = bridge.config

                    assert config['aprs_callsign'] == 'YAML-1'
                    assert config['aprs_passcode'] == '99999'
                    assert config['aprs_server'] == 'yaml.aprs.net'
                    assert config['message_prefix'] == 'YAMLTEST'

    def test_config_environment_overrides_yaml(self):
        """Test that environment variables override YAML configuration"""
        env_vars = {
            'APRS_CALLSIGN': 'ENV-OVERRIDE',
            'APRS_PASSCODE': '11111'
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch('os.path.exists') as mock_exists:
                def exists_side_effect(path):
                    return path == 'config.yaml'
                mock_exists.side_effect = exists_side_effect

                with patch('builtins.open', mock_open(read_data="""
aprs_callsign: "YAML-1"
aprs_passcode: "99999"
aprs_server: "yaml.aprs.net"
""")):
                    bridge = RARSMSBridge()
                    config = bridge.config

                    # Environment should override YAML
                    assert config['aprs_callsign'] == 'ENV-OVERRIDE'
                    assert config['aprs_passcode'] == '11111'
                    # YAML should provide fallback
                    assert config['aprs_server'] == 'yaml.aprs.net'

    def test_config_yaml_fallback_when_env_missing(self):
        """Test that YAML provides fallback when environment vars are not set"""
        # This tests the current bug - env vars set to None should use YAML values
        with patch.dict(os.environ, {}, clear=True):  # No env vars
            with patch('os.path.exists') as mock_exists:
                def exists_side_effect(path):
                    return path == 'config.yaml'
                mock_exists.side_effect = exists_side_effect

                with patch('builtins.open', mock_open(read_data="""
aprs_callsign: "YAML-FALLBACK"
aprs_passcode: "88888"
""")):
                    bridge = RARSMSBridge()
                    config = bridge.config

                    # YAML should be used when env vars are None
                    assert config['aprs_callsign'] == 'YAML-FALLBACK'
                    assert config['aprs_passcode'] == '88888'

    def test_load_callsigns_from_file(self, temp_callsigns_file):
        """Test loading authorized callsigns from file"""
        with patch('os.path.exists') as mock_exists:
            def exists_side_effect(path):
                return path == 'callsigns.txt'
            mock_exists.side_effect = exists_side_effect

            with patch('builtins.open', mock_open(read_data="""# Test callsigns
W4ABC
KJ4XYZ
N4DEF
# Comment line

""")):
                bridge = RARSMSBridge()
                callsigns = bridge.load_callsigns()

                assert 'W4ABC' in callsigns
                assert 'KJ4XYZ' in callsigns
                assert 'N4DEF' in callsigns
                assert len(callsigns) == 3  # Comments and empty lines ignored

    def test_load_callsigns_from_environment(self):
        """Test loading authorized callsigns from environment variable"""
        env_vars = {
            'AUTHORIZED_CALLSIGNS': 'W4ENV,KJ4ENV,N4ENV'
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with patch('os.path.exists', return_value=False):  # No callsigns.txt
                bridge = RARSMSBridge()
                callsigns = bridge.load_callsigns()

                assert 'W4ENV' in callsigns
                assert 'KJ4ENV' in callsigns
                assert 'N4ENV' in callsigns
                assert len(callsigns) == 3

    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):  # No files
                bridge = RARSMSBridge()
                config = bridge.config

                # Test defaults
                assert config['aprs_server'] == 'rotate.aprs2.net'
                assert config['aprs_port'] == 14580
                assert config['filter_distance'] == '100'
                assert config['filter_lat'] == '35.7796'
                assert config['filter_lon'] == '-78.6382'
                assert config['message_prefix'] == 'RARSMS'
                assert config['require_prefix'] is True
                assert config['discord_username'] == 'RARSMS Bridge'

    def test_boolean_environment_variable_parsing(self):
        """Test parsing of boolean environment variables"""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('yes', False),  # Only 'true' should be True
            ('1', False),    # Only 'true' should be True
        ]

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {'REQUIRE_PREFIX': env_value}, clear=True):
                with patch('os.path.exists', return_value=False):
                    bridge = RARSMSBridge()
                    assert bridge.config['require_prefix'] is expected

    def test_yaml_loading_error_handling(self):
        """Test that YAML loading errors are handled gracefully"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="invalid: yaml: content: {")):
                with patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML")):
                    # Should not raise exception
                    bridge = RARSMSBridge()
                    # Should fall back to environment/defaults
                    assert bridge.config['aprs_server'] == 'rotate.aprs2.net'

    def test_callsigns_file_error_handling(self):
        """Test that callsigns file errors are handled gracefully"""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("File read error")):
                bridge = RARSMSBridge()
                callsigns = bridge.load_callsigns()
                # Should return empty list on error
                assert callsigns == []

    def test_configuration_is_properly_configured_for_aprs(self):
        """Test detection of properly configured APRS"""
        with patch.dict(os.environ, {
            'APRS_CALLSIGN': 'W4TEST',
            'APRS_PASSCODE': '12345'
        }, clear=True):
            bridge = RARSMSBridge()

            # Should be considered configured
            assert bridge.config.get('aprs_callsign') == 'W4TEST'
            assert bridge.config.get('aprs_passcode') == '12345'

    def test_configuration_missing_aprs_credentials(self):
        """Test handling of missing APRS credentials"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):
                bridge = RARSMSBridge()

                # Should not be configured
                assert bridge.config.get('aprs_callsign') is None
                assert bridge.config.get('aprs_passcode') is None