"""Configuration management for RARSMS Discord Bot."""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiscordConfig:
    """Discord bot configuration."""
    token: str
    guild_id: str
    channel_id: str
    use_threads: bool = True
    command_prefix: str = "!"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    admin_email: str = ""
    admin_password: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "info"
    format: str = "json"
    output: str = "stdout"


@dataclass
class ServiceConfig:
    """Service-specific configuration."""
    enabled: bool = True
    reconnect_delay: int = 10
    message_timeout: int = 30


@dataclass
class Config:
    """Main application configuration."""
    discord: DiscordConfig
    database: DatabaseConfig
    logging: LoggingConfig
    service: ServiceConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file and environment variables."""
    # Default configuration
    config_data = {
        'discord': {
            'token': '',
            'guild_id': '',
            'channel_id': '',
            'use_threads': True,
            'command_prefix': '!'
        },
        'database': {
            'url': 'http://pocketbase:8090',
            'admin_email': '',
            'admin_password': ''
        },
        'logging': {
            'level': 'info',
            'format': 'json',
            'output': 'stdout'
        },
        'service': {
            'enabled': True,
            'reconnect_delay': 10,
            'message_timeout': 30
        }
    }

    # Load from config file if provided
    if config_path and Path(config_path).exists():
        with open(config_path, 'r') as f:
            file_config = yaml.safe_load(f)
            if file_config:
                _deep_update(config_data, file_config)

    # Override with environment variables
    _load_env_overrides(config_data)

    # Validate and create config objects
    return Config(
        discord=DiscordConfig(**config_data['discord']),
        database=DatabaseConfig(**config_data['database']),
        logging=LoggingConfig(**config_data['logging']),
        service=ServiceConfig(**config_data['service'])
    )


def _deep_update(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
    """Deep update a dictionary with another dictionary."""
    for key, value in update_dict.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            _deep_update(base_dict[key], value)
        else:
            base_dict[key] = value


def _load_env_overrides(config_data: Dict[str, Any]) -> None:
    """Load configuration overrides from environment variables."""
    # Discord configuration
    if token := os.getenv('DISCORD_TOKEN'):
        config_data['discord']['token'] = token
    if guild_id := os.getenv('DISCORD_GUILD_ID'):
        config_data['discord']['guild_id'] = guild_id
    if channel_id := os.getenv('DISCORD_CHANNEL_ID'):
        config_data['discord']['channel_id'] = channel_id
    if use_threads := os.getenv('DISCORD_USE_THREADS'):
        config_data['discord']['use_threads'] = use_threads.lower() == 'true'
    if prefix := os.getenv('DISCORD_COMMAND_PREFIX'):
        config_data['discord']['command_prefix'] = prefix

    # Database configuration
    if db_url := os.getenv('DATABASE_URL'):
        config_data['database']['url'] = db_url
    if admin_email := os.getenv('DATABASE_ADMIN_EMAIL'):
        config_data['database']['admin_email'] = admin_email
    if admin_password := os.getenv('DATABASE_ADMIN_PASSWORD'):
        config_data['database']['admin_password'] = admin_password

    # Logging configuration
    if log_level := os.getenv('LOG_LEVEL'):
        config_data['logging']['level'] = log_level.lower()
    if log_format := os.getenv('LOG_FORMAT'):
        config_data['logging']['format'] = log_format.lower()

    # Service configuration
    if enabled := os.getenv('DISCORD_BOT_ENABLED'):
        config_data['service']['enabled'] = enabled.lower() == 'true'
    if reconnect_delay := os.getenv('DISCORD_BOT_RECONNECT_DELAY'):
        try:
            config_data['service']['reconnect_delay'] = int(reconnect_delay)
        except ValueError:
            pass
    if timeout := os.getenv('DISCORD_BOT_MESSAGE_TIMEOUT'):
        try:
            config_data['service']['message_timeout'] = int(timeout)
        except ValueError:
            pass


def validate_config(config: Config) -> None:
    """Validate the configuration."""
    if not config.discord.token:
        raise ValueError("Discord token is required")
    if not config.discord.guild_id:
        raise ValueError("Discord guild ID is required")
    if not config.discord.channel_id:
        raise ValueError("Discord channel ID is required")
    if not config.database.url:
        raise ValueError("Database URL is required")

    # Validate log level
    valid_levels = {'debug', 'info', 'warning', 'error', 'critical'}
    if config.logging.level.lower() not in valid_levels:
        raise ValueError(f"Invalid log level: {config.logging.level}")

    # Validate log format
    valid_formats = {'json', 'text'}
    if config.logging.format.lower() not in valid_formats:
        raise ValueError(f"Invalid log format: {config.logging.format}")


# Environment-specific configuration helpers
def get_development_config() -> Dict[str, Any]:
    """Get development-specific configuration overrides."""
    return {
        'logging': {
            'level': 'debug',
            'format': 'text'
        },
        'service': {
            'reconnect_delay': 5
        }
    }


def get_production_config() -> Dict[str, Any]:
    """Get production-specific configuration overrides."""
    return {
        'logging': {
            'level': 'info',
            'format': 'json'
        },
        'service': {
            'reconnect_delay': 30
        }
    }