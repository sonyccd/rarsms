#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class NotificationData:
    """Data structure for notification content"""

    def __init__(self, packet_info: Dict[str, Any]):
        self.callsign = packet_info.get('callsign', 'Unknown')
        self.base_callsign = packet_info.get('base_callsign', 'Unknown')
        self.packet_type = packet_info.get('packet_type', 'unknown')
        self.timestamp = packet_info.get('timestamp', datetime.utcnow())
        self.raw_packet = packet_info.get('raw', '')
        self.position = packet_info.get('position')
        self.message = packet_info.get('message')

    def has_position(self) -> bool:
        """Check if this notification contains position data"""
        return self.position is not None

    def has_message(self) -> bool:
        """Check if this notification contains message data"""
        return self.message is not None

    def get_location_string(self) -> Optional[str]:
        """Get formatted location string if position is available"""
        if not self.has_position():
            return None

        pos = self.position
        return f"{pos['lat']:.4f}° N, {pos['lon']:.4f}° W"

    def get_message_text(self) -> Optional[str]:
        """Get formatted message text if message is available"""
        if not self.has_message():
            return None

        msg = self.message
        return f"To: {msg['addressee']}\n{msg['message']}"

class BaseNotifier(ABC):
    """Abstract base class for notification providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def send_notification(self, data: NotificationData) -> bool:
        """
        Send a notification with the given data.

        Args:
            data: NotificationData object containing packet information

        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if this notifier is properly configured and ready to use.

        Returns:
            bool: True if properly configured, False otherwise
        """
        pass

    def get_name(self) -> str:
        """Get the name of this notifier"""
        return self.name

    def validate_config(self) -> tuple[bool, str]:
        """
        Validate the configuration for this notifier.

        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        if self.is_configured():
            return True, "Configuration valid"
        else:
            return False, f"{self.name} is not properly configured"