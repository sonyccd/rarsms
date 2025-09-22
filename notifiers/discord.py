#!/usr/bin/env python3

import requests
import logging
from typing import Dict, Any
from .base import BaseNotifier, NotificationData

logger = logging.getLogger(__name__)

class DiscordNotifier(BaseNotifier):
    """Discord webhook notification provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('discord_webhook_url')
        self.username = config.get('discord_username', 'RARSMS Bridge')
        self.timeout = config.get('discord_timeout', 10)

    def is_configured(self) -> bool:
        """Check if Discord webhook URL is provided"""
        return bool(self.webhook_url and
                   self.webhook_url.strip() and
                   self.webhook_url.startswith('https://discord.com/api/webhooks/'))

    def send_notification(self, data: NotificationData) -> bool:
        """Send notification to Discord via webhook"""
        try:
            embed = self._create_embed(data)

            payload = {
                "username": self.username,
                "embeds": [embed]
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 204:
                logger.info(f"Sent Discord notification for {data.callsign}")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return False

    def _create_embed(self, data: NotificationData) -> Dict[str, Any]:
        """Create Discord embed from notification data"""
        embed = {
            "title": f"🚀 APRS Update from {data.callsign}",
            "color": self._get_color_for_packet_type(data.packet_type),
            "timestamp": data.timestamp.isoformat() + "Z",
            "fields": []
        }

        # Add position if available
        if data.has_position():
            embed["fields"].append({
                "name": "📍 Location",
                "value": data.get_location_string(),
                "inline": True
            })

        # Add message if available
        if data.has_message():
            embed["fields"].append({
                "name": "💬 Message",
                "value": data.get_message_text(),
                "inline": False
            })

        # Add packet type
        embed["fields"].append({
            "name": "📡 Type",
            "value": data.packet_type.title(),
            "inline": True
        })

        # Add raw packet for debugging (truncated)
        raw_packet = data.raw_packet[:1000] if len(data.raw_packet) > 1000 else data.raw_packet
        embed["fields"].append({
            "name": "🔍 Raw Packet",
            "value": f"```{raw_packet}```",
            "inline": False
        })

        return embed

    def _get_color_for_packet_type(self, packet_type: str) -> int:
        """Get color code based on packet type"""
        color_map = {
            'position': 0x00ff00,  # Green
            'message': 0x0099ff,   # Blue
            'unknown': 0xff9900    # Orange
        }
        return color_map.get(packet_type, 0xff9900)

    def validate_config(self) -> tuple[bool, str]:
        """Validate Discord-specific configuration"""
        if not self.webhook_url or not self.webhook_url.strip():
            return False, "Discord webhook URL not provided"

        if not self.webhook_url.startswith('https://discord.com/api/webhooks/'):
            return False, "Invalid Discord webhook URL format"

        # Test webhook with a simple request (optional)
        try:
            response = requests.get(self.webhook_url, timeout=5)
            if response.status_code == 200:
                return True, "Discord webhook is accessible"
            else:
                return False, f"Discord webhook returned status {response.status_code}"
        except Exception as e:
            return False, f"Could not validate Discord webhook: {e}"