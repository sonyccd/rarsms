#!/usr/bin/env python3

import logging
from typing import Dict, Any, List, Type
from .base import BaseNotifier, NotificationData
from .discord import DiscordNotifier
from .slack import SlackNotifier
from .email import EmailNotifier
from .file import FileNotifier

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages multiple notification providers"""

    def __init__(self):
        self.notifiers: List[BaseNotifier] = []
        self.registry: Dict[str, Type[BaseNotifier]] = {
            'discord': DiscordNotifier,
            'slack': SlackNotifier,
            'email': EmailNotifier,
            'file': FileNotifier,
        }

    def register_notifier(self, name: str, notifier_class: Type[BaseNotifier]):
        """Register a new notifier type"""
        self.registry[name] = notifier_class
        logger.info(f"Registered notifier: {name}")

    def add_notifier_from_config(self, notifier_type: str, config: Dict[str, Any]) -> bool:
        """
        Add a notifier instance from configuration

        Args:
            notifier_type: Type of notifier (e.g., 'discord', 'slack', etc.)
            config: Configuration dictionary for the notifier

        Returns:
            bool: True if notifier was added successfully
        """
        if notifier_type not in self.registry:
            logger.error(f"Unknown notifier type: {notifier_type}")
            return False

        try:
            notifier_class = self.registry[notifier_type]
            notifier = notifier_class(config)

            # Validate configuration
            is_valid, error_message = notifier.validate_config()
            if not is_valid:
                logger.error(f"Invalid configuration for {notifier_type}: {error_message}")
                return False

            self.notifiers.append(notifier)
            logger.info(f"Added {notifier_type} notifier: {notifier.get_name()}")
            return True

        except Exception as e:
            logger.error(f"Error creating {notifier_type} notifier: {e}")
            return False

    def load_notifiers_from_config(self, config: Dict[str, Any]):
        """
        Load all configured notifiers from the main configuration

        Args:
            config: Main application configuration
        """
        # Load Discord notifier if configured
        webhook_url = config.get('discord_webhook_url')
        if webhook_url and webhook_url.strip() and webhook_url.startswith('https://discord.com/api/webhooks/'):
            discord_config = {
                'discord_webhook_url': webhook_url,
                'discord_username': config.get('discord_username', 'RARSMS Bridge'),
                'discord_timeout': config.get('discord_timeout', 10)
            }
            self.add_notifier_from_config('discord', discord_config)
        else:
            logger.info("📤 Legacy Discord notifications not configured (using protocol system instead)")

        # Load other notifiers from dedicated configuration sections
        notifiers_config = config.get('notifiers', {}) or {}
        if notifiers_config:
            for notifier_type, notifier_config in notifiers_config.items():
                if notifier_config.get('enabled', True):
                    self.add_notifier_from_config(notifier_type, notifier_config)

        if len(self.notifiers) > 0:
            logger.info(f"📬 Loaded {len(self.notifiers)} legacy notification providers")
        else:
            logger.info("📭 No legacy notification providers configured")

    def send_notification(self, packet_info: Dict[str, Any]) -> int:
        """
        Send notification to all configured notifiers

        Args:
            packet_info: Packet information dictionary

        Returns:
            int: Number of successful notifications sent
        """
        if not self.notifiers:
            logger.warning("No notifiers configured")
            return 0

        data = NotificationData(packet_info)
        success_count = 0

        for notifier in self.notifiers:
            try:
                if notifier.send_notification(data):
                    success_count += 1
                else:
                    logger.warning(f"Failed to send notification via {notifier.get_name()}")
            except Exception as e:
                logger.error(f"Error sending notification via {notifier.get_name()}: {e}")

        logger.info(f"Sent notifications via {success_count}/{len(self.notifiers)} notifiers")
        return success_count

    def get_notifier_count(self) -> int:
        """Get the number of configured notifiers"""
        return len(self.notifiers)

    def get_notifier_names(self) -> List[str]:
        """Get list of configured notifier names"""
        return [notifier.get_name() for notifier in self.notifiers]

    def validate_all_notifiers(self) -> Dict[str, tuple[bool, str]]:
        """
        Validate all configured notifiers

        Returns:
            Dict[str, tuple[bool, str]]: Validation results for each notifier
        """
        results = {}
        for notifier in self.notifiers:
            results[notifier.get_name()] = notifier.validate_config()
        return results