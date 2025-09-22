#!/usr/bin/env python3

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
import discord
from discord.ext import commands
from .base import BaseProtocol, Message, MessageType, ProtocolCapabilities

logger = logging.getLogger(__name__)

class DiscordBotProtocol(BaseProtocol):
    """Discord bot protocol for bidirectional communication"""

    def __init__(self, protocol_name: str, config: Dict[str, Any]):
        super().__init__(protocol_name, config)

        # Discord bot configuration
        self.bot_token = config.get('discord_bot_token')
        self.channel_id = config.get('discord_channel_id')
        self.guild_id = config.get('discord_guild_id')  # Optional

        # Bot instance
        self.bot = None
        self.channel = None

        # Message tracking for replies
        self.aprs_message_map = {}  # Discord message ID -> APRS callsign

    def is_configured(self) -> bool:
        """Check if Discord bot is properly configured"""
        return bool(self.bot_token and self.channel_id)

    def get_capabilities(self) -> ProtocolCapabilities:
        """Get Discord bot protocol capabilities"""
        return ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            supports_position=True,
            supports_threading=True,
            supports_attachments=True,
            max_message_length=2000
        )

    async def connect(self) -> bool:
        """Connect to Discord via bot"""
        try:
            if not self.is_configured():
                logger.error("Discord bot not configured - missing token or channel ID")
                return False

            # Set up bot with intents
            intents = discord.Intents.default()
            intents.message_content = True
            intents.messages = True

            self.bot = commands.Bot(command_prefix='!', intents=intents)

            # Set up event handlers
            self._setup_event_handlers()

            # Start bot in background
            asyncio.create_task(self._start_bot())

            # Wait a moment for connection
            await asyncio.sleep(2)

            if self.bot.is_ready():
                self.channel = self.bot.get_channel(int(self.channel_id))
                if self.channel:
                    self.is_connected = True
                    logger.info(f"✅ Discord bot connected to channel: {self.channel.name}")
                    return True
                else:
                    logger.error(f"❌ Could not find Discord channel with ID: {self.channel_id}")
                    return False
            else:
                logger.warning("Discord bot connection still pending...")
                return True  # Connection is async, may take time

        except Exception as e:
            logger.error(f"❌ Failed to connect Discord bot: {e}")
            return False

    def _setup_event_handlers(self):
        """Set up Discord bot event handlers"""

        @self.bot.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.bot.user}")
            self.channel = self.bot.get_channel(int(self.channel_id))
            if self.channel:
                self.is_connected = True
                logger.info(f"✅ Discord bot ready - monitoring channel: {self.channel.name}")

        @self.bot.event
        async def on_message(discord_message):
            # Ignore bot's own messages
            if discord_message.author == self.bot.user:
                return

            # Only process messages from our target channel
            if discord_message.channel.id != int(self.channel_id):
                return

            await self._handle_discord_message(discord_message)

    async def _start_bot(self):
        """Start the Discord bot"""
        try:
            await self.bot.start(self.bot_token)
        except Exception as e:
            logger.error(f"Discord bot startup error: {e}")

    async def _handle_discord_message(self, discord_message):
        """Handle incoming Discord messages and check for APRS replies"""
        try:
            # Check if this is a reply to a message
            if discord_message.reference and discord_message.reference.message_id:
                original_message_id = discord_message.reference.message_id

                # Check if the original message was from APRS
                if original_message_id in self.aprs_message_map:
                    aprs_callsign = self.aprs_message_map[original_message_id]

                    # Parse the reply for APRS command
                    parsed_reply = self._parse_aprs_reply(discord_message.content)
                    if parsed_reply:
                        target_callsign, message_content = parsed_reply
                        logger.info(f"🔍 Parsed APRS reply: target='{target_callsign}', content='{message_content}'")

                        # Verify the target callsign matches the original sender
                        if target_callsign.upper() == aprs_callsign.upper():
                            # Create message to send back to APRS
                            reply_message = Message(
                                source_protocol=self.name,
                                source_id=f"{discord_message.author.display_name}#{discord_message.author.discriminator}",
                                message_type=MessageType.TEXT,
                                content=message_content,
                                metadata={
                                    'discord_user_id': discord_message.author.id,
                                    'discord_channel_id': discord_message.channel.id,
                                    'target_callsign': target_callsign,
                                    'reply_to_aprs': True
                                }
                            )

                            # Add APRS as target protocol with specific callsign
                            reply_message.add_target('aprs_main')
                            reply_message.target_ids['aprs'] = target_callsign

                            # Send via callback
                            logger.info(f"🔍 Created reply message: content='{reply_message.content}', target_ids={reply_message.target_ids}, metadata={reply_message.metadata}")
                            if self.message_callback:
                                self.message_callback(reply_message)

                            logger.info(f"📤 Discord reply routed to APRS: {target_callsign}")

                            # React to show message was processed
                            await discord_message.add_reaction("📡")
                        else:
                            # Wrong callsign in reply
                            await discord_message.add_reaction("❌")
                            logger.warning(f"Reply callsign mismatch: expected {aprs_callsign}, got {target_callsign}")
                    else:
                        # Not a valid APRS reply format
                        logger.debug("Discord reply doesn't match APRS format")

        except Exception as e:
            logger.error(f"Error handling Discord message: {e}")

    def _parse_aprs_reply(self, content: str) -> Optional[tuple]:
        """
        Parse Discord message for APRS reply format: 'APRS <callsign> <message>'
        Returns: (callsign, message) or None if not valid format
        """
        # Pattern: APRS followed by callsign followed by message
        pattern = r'^APRS\s+([A-Z0-9\-/]+)\s+(.+)$'
        match = re.match(pattern, content.strip(), re.IGNORECASE)

        if match:
            callsign = match.group(1).upper()
            message = match.group(2).strip()

            # Validate callsign format (basic amateur radio callsign validation)
            # Supports both SSID (-15) and portable/mobile indicators (/M, /P, etc.)
            # Pattern: 1-2 letters, 1 digit, 1-3 letters, optional SSID, optional portable indicator
            if re.match(r'^[A-Z]{1,2}[0-9][A-Z]{1,3}(-[0-9A-Z]+)?(/[A-Z0-9]+)?$', callsign):
                return (callsign, message)

        return None

    async def send_message(self, message: Message) -> bool:
        """Send message to Discord channel"""
        try:
            if not self.is_connected or not self.channel:
                logger.warning("Discord bot not connected")
                return False

            # Check if this is a reply to APRS
            if message.metadata.get('reply_to_aprs'):
                # This is a reply going back to APRS, don't send to Discord
                return True

            # Format message for Discord
            formatted_content = self._format_message_for_discord(message)

            # Send message
            sent_message = await self.channel.send(formatted_content)

            # Track this message for potential replies
            if message.source_protocol.startswith('aprs'):
                self.aprs_message_map[sent_message.id] = message.source_id

                # Clean up old mappings (keep last 100)
                if len(self.aprs_message_map) > 100:
                    oldest_keys = list(self.aprs_message_map.keys())[:-100]
                    for key in oldest_keys:
                        del self.aprs_message_map[key]

            logger.info(f"📤 Sent Discord message: {message.source_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send Discord message: {e}")
            return False

    def _format_message_for_discord(self, message: Message) -> str:
        """Format message for Discord with rich formatting"""

        # Get message type emoji
        emoji_map = {
            MessageType.TEXT: "💬",
            MessageType.POSITION: "📍",
            MessageType.EMERGENCY: "🚨",
            MessageType.STATUS: "ℹ️"
        }
        emoji = emoji_map.get(message.message_type, "📨")

        # Format header
        header = f"{emoji} **{message.source_id}** ({message.source_protocol})"

        # Format content
        content = message.content or "No content"

        # Add position information if available
        position_info = ""
        if hasattr(message, 'get_position') and message.get_position():
            pos = message.get_position()
            lat, lon = pos['lat'], pos['lon']
            map_url = f"https://maps.google.com/?q={lat},{lon}"
            position_info = f"\n📍 Location: [{lat:.4f}, {lon:.4f}]({map_url})"

        # Add timestamp
        timestamp = f"\n🕐 {message.timestamp.strftime('%H:%M:%S UTC')}"

        # Combine all parts
        formatted = f"{header}\n{content}{position_info}{timestamp}"

        # Add reply instructions for APRS messages
        if message.source_protocol.startswith('aprs'):
            formatted += f"\n\n*Reply with: `APRS {message.source_id} <your message>`*"

        return formatted

    async def disconnect(self) -> bool:
        """Disconnect from Discord"""
        try:
            if self.bot:
                await self.bot.close()
                self.is_connected = False
                logger.info("Discord bot disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting Discord bot: {e}")
            return False

    def get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol information"""
        return {
            'name': self.name,
            'type': 'discord_bot',
            'connected': self.is_connected,
            'capabilities': {
                'can_send': self.capabilities.can_send,
                'can_receive': self.capabilities.can_receive,
                'supports_position': self.capabilities.supports_position,
                'supports_threading': self.capabilities.supports_threading,
                'supports_attachments': self.capabilities.supports_attachments,
                'max_message_length': self.capabilities.max_message_length
            },
            'channel_id': self.channel_id,
            'bot_user': str(self.bot.user) if self.bot and self.bot.user else None,
            'tracked_messages': len(self.aprs_message_map)
        }