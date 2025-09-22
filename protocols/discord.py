#!/usr/bin/env python3

import asyncio
import logging
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseProtocol, Message, MessageType, ProtocolCapabilities

logger = logging.getLogger(__name__)

class DiscordProtocol(BaseProtocol):
    """Discord protocol implementation for bidirectional communication"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)

        # Discord configuration
        self.webhook_url = config.get('discord_webhook_url')
        self.bot_token = config.get('discord_bot_token')  # For bidirectional support
        self.channel_id = config.get('discord_channel_id')  # Channel to monitor
        self.username = config.get('discord_username', 'RARSMS Bridge')
        self.timeout = config.get('discord_timeout', 10)

        # For receiving messages (requires bot token and channel monitoring)
        self.last_message_id: Optional[str] = None
        self.poll_interval = config.get('discord_poll_interval', 5)
        self.poll_task: Optional[asyncio.Task] = None

    def get_capabilities(self) -> ProtocolCapabilities:
        """Discord capabilities"""
        return ProtocolCapabilities(
            can_send=bool(self.webhook_url),
            can_receive=bool(self.bot_token and self.channel_id),
            supports_position=True,
            supports_threading=True,
            supports_attachments=True,
            max_message_length=2000
        )

    def is_configured(self) -> bool:
        """Check if Discord is properly configured"""
        return bool(self.webhook_url)  # Minimum requirement for sending

    async def connect(self) -> bool:
        """Connect to Discord services"""
        try:
            # Test webhook if available
            if self.webhook_url:
                test_success = await self._test_webhook()
                if not test_success:
                    logger.error(f"Discord webhook test failed for protocol '{self.name}'")
                    return False

            # Start polling for incoming messages if bot token is available
            if self.capabilities.can_receive:
                self.poll_task = asyncio.create_task(self._poll_messages())
                logger.info(f"Started Discord message polling for protocol '{self.name}'")

            self.is_connected = True
            logger.info(f"Discord protocol '{self.name}' connected successfully")
            return True

        except Exception as e:
            logger.error(f"Error connecting Discord protocol '{self.name}': {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Discord services"""
        try:
            self.is_connected = False

            # Cancel polling task
            if self.poll_task:
                self.poll_task.cancel()
                try:
                    await self.poll_task
                except asyncio.CancelledError:
                    pass
                self.poll_task = None

            logger.info(f"Discord protocol '{self.name}' disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting Discord protocol '{self.name}': {e}")
            return False

    async def send_message(self, message: Message) -> bool:
        """Send a message via Discord webhook"""
        try:
            if not self.webhook_url:
                logger.error(f"No webhook URL configured for Discord protocol '{self.name}'")
                return False

            # Validate message
            is_valid, error = self.validate_message(message)
            if not is_valid:
                logger.error(f"Invalid message for Discord: {error}")
                return False

            # Create Discord payload
            if message.message_type == MessageType.POSITION:
                payload = self._create_position_embed(message)
            else:
                payload = self._create_text_message(message)

            # Send via webhook
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout
                )
            )

            if response.status_code == 204:
                logger.info(f"Sent Discord message from {message.source_protocol}:{message.source_id}")
                return True
            else:
                logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return False

    async def _test_webhook(self) -> bool:
        """Test Discord webhook connectivity"""
        try:
            test_payload = {
                "username": self.username,
                "content": "🔗 RARSMS Bridge connection test",
                "flags": 1 << 6  # Ephemeral message (auto-delete)
            }

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    self.webhook_url,
                    json=test_payload,
                    timeout=self.timeout
                )
            )

            return response.status_code == 204

        except Exception as e:
            logger.error(f"Discord webhook test failed: {e}")
            return False

    async def _poll_messages(self):
        """Poll Discord channel for new messages"""
        try:
            headers = {
                'Authorization': f'Bot {self.bot_token}',
                'Content-Type': 'application/json'
            }

            while self.is_connected:
                try:
                    # Get recent messages
                    url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
                    params = {'limit': 10}

                    if self.last_message_id:
                        params['after'] = self.last_message_id

                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: requests.get(url, headers=headers, params=params, timeout=self.timeout)
                    )

                    if response.status_code == 200:
                        messages = response.json()

                        # Process new messages (reverse order for chronological processing)
                        for discord_msg in reversed(messages):
                            await self._process_discord_message(discord_msg)

                        # Update last message ID
                        if messages:
                            self.last_message_id = messages[0]['id']

                    elif response.status_code == 429:
                        # Rate limited, wait longer
                        rate_limit_reset = response.headers.get('X-RateLimit-Reset-After', '60')
                        await asyncio.sleep(float(rate_limit_reset))
                        continue

                    # Wait before next poll
                    await asyncio.sleep(self.poll_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error polling Discord messages: {e}")
                    await asyncio.sleep(self.poll_interval * 2)  # Back off on error

        except asyncio.CancelledError:
            logger.debug("Discord message polling cancelled")
        except Exception as e:
            logger.error(f"Discord polling error: {e}")

    async def _process_discord_message(self, discord_msg: Dict[str, Any]):
        """Process incoming Discord message"""
        try:
            # Skip bot messages and webhooks
            if discord_msg.get('webhook_id') or discord_msg.get('bot'):
                return

            # Skip our own messages
            if discord_msg.get('author', {}).get('username') == self.username:
                return

            message = self.parse_incoming_message(discord_msg)
            if message:
                logger.info(f"Received Discord message from {message.source_id}")
                self.on_message_received(message)

        except Exception as e:
            logger.debug(f"Error processing Discord message: {e}")

    def parse_incoming_message(self, discord_msg: Dict[str, Any]) -> Optional[Message]:
        """Parse Discord message into standardized Message"""
        try:
            author = discord_msg.get('author', {})
            content = discord_msg.get('content', '').strip()

            if not content:
                return None

            # Extract user info
            username = author.get('username', 'Unknown')
            user_id = author.get('id', 'unknown')
            source_id = f"{username}#{author.get('discriminator', '0000')}"

            # Determine message type
            message_type = MessageType.TEXT

            # Check for position data in embeds or content
            position = None
            embeds = discord_msg.get('embeds', [])
            for embed in embeds:
                if 'location' in embed.get('title', '').lower():
                    # Try to extract coordinates from embed
                    position = self._extract_position_from_embed(embed)
                    if position:
                        message_type = MessageType.POSITION
                        break

            # Create standardized message
            return Message(
                source_protocol=self.name,
                source_id=source_id,
                message_type=message_type,
                content=content,
                timestamp=datetime.fromisoformat(discord_msg['timestamp'].replace('Z', '+00:00')),
                metadata={
                    'discord_user_id': user_id,
                    'discord_message_id': discord_msg['id'],
                    'discord_channel_id': discord_msg['channel_id'],
                    'position': position
                }
            )

        except Exception as e:
            logger.debug(f"Error parsing Discord message: {e}")
            return None

    def _create_text_message(self, message: Message) -> Dict[str, Any]:
        """Create Discord text message payload"""
        # Format content with source info
        formatted_content = f"**[{message.source_protocol.upper()}]** {message.source_id}: {message.content}"

        return {
            "username": self.username,
            "content": formatted_content[:2000]  # Discord limit
        }

    def _create_position_embed(self, message: Message) -> Dict[str, Any]:
        """Create Discord embed for position messages"""
        position = message.get_position()

        embed = {
            "title": f"📍 Position Update from {message.source_id}",
            "color": 0x00ff00,
            "timestamp": message.timestamp.isoformat() + "Z",
            "fields": [
                {
                    "name": "Protocol",
                    "value": message.source_protocol.upper(),
                    "inline": True
                }
            ]
        }

        if position:
            embed["fields"].append({
                "name": "Location",
                "value": f"{position['lat']:.6f}°, {position['lon']:.6f}°",
                "inline": True
            })

            # Add Google Maps link
            maps_url = f"https://maps.google.com/?q={position['lat']},{position['lon']}"
            embed["fields"].append({
                "name": "Map Link",
                "value": f"[View on Google Maps]({maps_url})",
                "inline": False
            })

        if message.content:
            embed["description"] = message.content

        return {
            "username": self.username,
            "embeds": [embed]
        }

    def _extract_position_from_embed(self, embed: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract position coordinates from Discord embed"""
        try:
            # Look for coordinates in various embed fields
            for field in embed.get('fields', []):
                field_value = field.get('value', '')
                if '°' in field_value and ',' in field_value:
                    # Try to parse coordinates
                    import re
                    coord_match = re.search(r'(-?\d+\.?\d*)°.*?(-?\d+\.?\d*)°', field_value)
                    if coord_match:
                        lat = float(coord_match.group(1))
                        lon = float(coord_match.group(2))
                        return {'lat': lat, 'lon': lon}

            return None

        except Exception:
            return None

    def format_message_for_protocol(self, message: Message) -> str:
        """Format message for Discord (override base implementation)"""
        if message.message_type == MessageType.POSITION:
            position = message.get_position()
            if position:
                return f"📍 {message.source_id} shared location: {position['lat']:.4f}, {position['lon']:.4f}"

        return f"💬 {message.source_id}: {message.content}"