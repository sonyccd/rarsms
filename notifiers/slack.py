#!/usr/bin/env python3

import requests
import logging
from typing import Dict, Any
from .base import BaseNotifier, NotificationData

logger = logging.getLogger(__name__)

class SlackNotifier(BaseNotifier):
    """Slack webhook notification provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get('slack_webhook_url')
        self.username = config.get('slack_username', 'RARSMS Bridge')
        self.channel = config.get('slack_channel', '#general')
        self.timeout = config.get('slack_timeout', 10)

    def is_configured(self) -> bool:
        """Check if Slack webhook URL is provided"""
        return bool(self.webhook_url and self.webhook_url.startswith('https://hooks.slack.com/'))

    def send_notification(self, data: NotificationData) -> bool:
        """Send notification to Slack via webhook"""
        try:
            blocks = self._create_blocks(data)

            payload = {
                "username": self.username,
                "channel": self.channel,
                "blocks": blocks
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info(f"Sent Slack notification for {data.callsign}")
                return True
            else:
                logger.error(f"Slack webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False

    def _create_blocks(self, data: NotificationData) -> list:
        """Create Slack blocks from notification data"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📡 APRS Update from {data.callsign}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:* {data.packet_type.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:* {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                    }
                ]
            }
        ]

        # Add position if available
        if data.has_position():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📍 Location:* {data.get_location_string()}"
                }
            })

        # Add message if available
        if data.has_message():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💬 Message:*\n{data.get_message_text()}"
                }
            })

        # Add raw packet in a code block
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Raw Packet:*\n```{data.raw_packet[:500]}```"
            }
        })

        return blocks

    def validate_config(self) -> tuple[bool, str]:
        """Validate Slack-specific configuration"""
        if not self.webhook_url:
            return False, "Slack webhook URL not provided"

        if not self.webhook_url.startswith('https://hooks.slack.com/'):
            return False, "Invalid Slack webhook URL format"

        return True, "Slack configuration valid"