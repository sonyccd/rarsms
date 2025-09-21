"""Discord bot for RARSMS message routing."""

import asyncio
import re
from typing import Optional, Dict, Any

import discord
from discord.ext import commands, tasks
import structlog

from config import Config
from database import DatabaseClient

logger = structlog.get_logger()


class RARSMSBot(commands.Bot):
    """RARSMS Discord Bot for message routing."""

    def __init__(self, config: Config, database: DatabaseClient):
        self.config = config
        self.database = database

        # Bot configuration
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix=config.discord.command_prefix,
            intents=intents,
            help_command=None
        )

        # State tracking
        self.target_guild: Optional[discord.Guild] = None
        self.target_channel: Optional[discord.TextChannel] = None
        self.ready_event = asyncio.Event()

    async def setup_hook(self):
        """Setup hook called when bot is starting."""
        logger.info("Setting up RARSMS Discord Bot")

        # Start background tasks
        self.check_pending_messages.start()
        self.update_status.start()

    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(
            "Bot logged in",
            user=str(self.user),
            guilds=len(self.guilds)
        )

        # Find target guild and channel
        await self._setup_target_channel()

        # Update system status
        await self.database.update_system_status(
            service="discord-bot",
            status="online",
            metadata={
                "bot_user": str(self.user),
                "guild_count": len(self.guilds),
                "connected_at": discord.utils.utcnow().isoformat()
            }
        )

        self.ready_event.set()

    async def on_disconnect(self):
        """Called when bot disconnects."""
        logger.warning("Bot disconnected from Discord")
        await self.database.update_system_status(
            service="discord-bot",
            status="offline",
            metadata={"disconnected_at": discord.utils.utcnow().isoformat()}
        )

    async def on_resumed(self):
        """Called when bot resumes connection."""
        logger.info("Bot resumed connection to Discord")

    async def on_error(self, event, *args, **kwargs):
        """Handle bot errors."""
        logger.error("Bot error occurred", event=event, args=args)

        await self.database.log_event(
            level="error",
            service="discord",
            event_type="error",
            message=f"Bot error in event {event}",
            metadata={"event": event, "args": str(args)}
        )

    async def on_message(self, message: discord.Message):
        """Handle incoming Discord messages."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Only process messages in threads created by the bot
        if isinstance(message.channel, discord.Thread):
            await self._handle_thread_reply(message)

        # Process commands
        await self.process_commands(message)

    async def _setup_target_channel(self):
        """Setup target guild and channel."""
        try:
            guild_id = int(self.config.discord.guild_id)
            channel_id = int(self.config.discord.channel_id)

            self.target_guild = self.get_guild(guild_id)
            if not self.target_guild:
                raise ValueError(f"Guild {guild_id} not found")

            self.target_channel = self.target_guild.get_channel(channel_id)
            if not self.target_channel:
                raise ValueError(f"Channel {channel_id} not found")

            logger.info(
                "Target channel configured",
                guild=self.target_guild.name,
                channel=self.target_channel.name
            )

        except Exception as e:
            logger.error("Failed to setup target channel", error=str(e))
            raise

    async def _handle_thread_reply(self, message: discord.Message):
        """Handle replies in threads created by the bot."""
        thread = message.channel

        # Get thread information from database
        thread_record = await self.database.get_discord_thread_by_id(str(thread.id))
        if not thread_record:
            logger.debug("Thread not found in database", thread_id=thread.id)
            return

        correlation_id = thread_record['correlation_id']

        # Get user information
        user_profile = await self.database.get_user_by_discord_id(str(message.author.id))
        if not user_profile:
            logger.debug("User not found in database", discord_id=message.author.id)
            # Could still allow the message but without user linking
            user_id = None
            callsign = f"Discord-{message.author.display_name}"
        else:
            user_id = user_profile.get('user')
            callsign = user_profile.get('callsign', f"Discord-{message.author.display_name}")

        # Create reply message for routing to APRS
        message_data = {
            'correlation_id': correlation_id,
            'from_callsign': callsign,
            'from_service': 'discord',
            'to_service': 'aprs',
            'content': message.content,
            'message_type': 'reply',
            'status': 'pending',
            'thread_id': str(thread.id),
            'metadata': {
                'discord_message_id': str(message.id),
                'discord_author': str(message.author),
                'discord_author_id': str(message.author.id),
                'thread_name': thread.name
            }
        }

        if user_id:
            message_data['user'] = user_id

        # Store message for routing
        message_id = await self.database.create_message(message_data)
        if message_id:
            logger.info(
                "Discord reply queued for APRS",
                message_id=message_id,
                correlation_id=correlation_id,
                author=str(message.author)
            )

            # Update thread activity
            await self.database.update_discord_thread_activity(str(thread.id))

            # Update conversation
            await self.database.create_or_update_conversation(
                correlation_id, user_id, message.content
            )

            # Add reaction to show message was processed
            try:
                await message.add_reaction('📡')
            except discord.HTTPException:
                pass

        else:
            logger.error("Failed to store Discord reply", correlation_id=correlation_id)

    async def post_aprs_message(
        self,
        from_callsign: str,
        content: str,
        correlation_id: str,
        message_id: str
    ) -> bool:
        """Post an APRS message to Discord."""
        if not self.target_channel:
            logger.error("Target channel not configured")
            return False

        try:
            # Format message for Discord
            formatted_content = f"**📡 APRS Message from {from_callsign}**\n```{content}```"

            # Create thread if configured
            if self.config.discord.use_threads:
                # Create thread for the conversation
                thread_name = f"{from_callsign} - {content[:30]}..."
                if len(thread_name) > 100:
                    thread_name = thread_name[:97] + "..."

                # Post initial message
                initial_message = await self.target_channel.send(formatted_content)

                # Create thread
                thread = await initial_message.create_thread(
                    name=thread_name,
                    auto_archive_duration=1440  # 24 hours
                )

                # Store thread information
                user_profile = None
                # Try to find user by callsign
                # This would require a different database query - simplified for now

                await self.database.create_discord_thread_record(
                    thread_id=str(thread.id),
                    channel_id=str(self.target_channel.id),
                    correlation_id=correlation_id,
                    user_id=None,  # Would need callsign lookup
                    thread_name=thread_name
                )

                # Post instructions in thread
                instructions = (
                    f"💬 **Thread created for conversation with {from_callsign}**\n\n"
                    "Reply in this thread to send messages back to the APRS station. "
                    "Your replies will be automatically forwarded via APRS-IS."
                )
                await thread.send(instructions)

                logger.info(
                    "APRS message posted to Discord with thread",
                    from_callsign=from_callsign,
                    thread_id=thread.id,
                    correlation_id=correlation_id
                )

            else:
                # Just post message without thread
                await self.target_channel.send(formatted_content)

                logger.info(
                    "APRS message posted to Discord",
                    from_callsign=from_callsign,
                    correlation_id=correlation_id
                )

            return True

        except discord.HTTPException as e:
            logger.error("Failed to post message to Discord", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error posting to Discord", error=str(e))
            return False

    @tasks.loop(seconds=10)
    async def check_pending_messages(self):
        """Check for pending messages to post to Discord."""
        if not self.ready_event.is_set():
            return

        try:
            pending_messages = await self.database.get_pending_messages("discord")

            for msg_data in pending_messages:
                message_id = msg_data['id']
                from_callsign = msg_data['from_callsign']
                content = msg_data['content']
                correlation_id = msg_data['correlation_id']

                # Post to Discord
                success = await self.post_aprs_message(
                    from_callsign, content, correlation_id, message_id
                )

                # Update message status
                if success:
                    await self.database.update_message_status(
                        message_id,
                        "delivered",
                        metadata={
                            "delivered_via": "discord",
                            "channel_id": str(self.target_channel.id) if self.target_channel else None
                        }
                    )

                    await self.database.log_event(
                        level="info",
                        service="discord",
                        event_type="message",
                        message=f"Message from {from_callsign} posted to Discord",
                        metadata={
                            "message_id": message_id,
                            "from_callsign": from_callsign,
                            "correlation_id": correlation_id
                        },
                        correlation_id=correlation_id
                    )
                else:
                    await self.database.update_message_status(
                        message_id,
                        "failed",
                        metadata={"error": "Failed to post to Discord"}
                    )

                # Small delay between messages
                await asyncio.sleep(2)

        except Exception as e:
            logger.error("Error checking pending messages", error=str(e))

    @check_pending_messages.before_loop
    async def before_check_pending_messages(self):
        """Wait for bot to be ready before checking messages."""
        await self.ready_event.wait()

    @tasks.loop(minutes=5)
    async def update_status(self):
        """Update bot status periodically."""
        if not self.ready_event.is_set():
            return

        try:
            await self.database.update_system_status(
                service="discord-bot",
                status="online",
                metadata={
                    "last_heartbeat": discord.utils.utcnow().isoformat(),
                    "guild_count": len(self.guilds),
                    "latency": round(self.latency * 1000, 2)  # ms
                }
            )
        except Exception as e:
            logger.error("Failed to update status", error=str(e))

    @update_status.before_loop
    async def before_update_status(self):
        """Wait for bot to be ready before updating status."""
        await self.ready_event.wait()

    @commands.command(name='status')
    async def status_command(self, ctx):
        """Check bot status."""
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        # Only respond in the configured channel or DMs
        if ctx.channel.id != int(self.config.discord.channel_id) and not isinstance(ctx.channel, discord.DMChannel):
            return

        embed = discord.Embed(
            title="🤖 RARSMS Bot Status",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="📡 Connection",
            value=f"✅ Connected\nLatency: {round(self.latency * 1000)}ms",
            inline=True
        )

        embed.add_field(
            name="🏠 Server",
            value=f"Guild: {self.target_guild.name if self.target_guild else 'Unknown'}\nChannel: {self.target_channel.name if self.target_channel else 'Unknown'}",
            inline=True
        )

        embed.add_field(
            name="⚙️ Configuration",
            value=f"Threads: {'✅ Enabled' if self.config.discord.use_threads else '❌ Disabled'}\nPrefix: {self.config.discord.command_prefix}",
            inline=True
        )

        await ctx.send(embed=embed)

    @commands.command(name='help')
    async def help_command(self, ctx):
        """Show help information."""
        if not isinstance(ctx.channel, discord.TextChannel):
            return

        # Only respond in the configured channel or DMs
        if ctx.channel.id != int(self.config.discord.channel_id) and not isinstance(ctx.channel, discord.DMChannel):
            return

        embed = discord.Embed(
            title="📡 RARSMS Discord Bot",
            description="Bridging APRS and Discord for the Raleigh Amateur Radio Society",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="🔄 How it works",
            value=(
                "• APRS messages to 'RARSMS' appear here\n"
                "• Reply in threads to send messages back\n"
                "• Automatic message routing between platforms"
            ),
            inline=False
        )

        embed.add_field(
            name="🛠️ Commands",
            value=(
                f"`{self.config.discord.command_prefix}status` - Check bot status\n"
                f"`{self.config.discord.command_prefix}help` - Show this help"
            ),
            inline=False
        )

        embed.add_field(
            name="ℹ️ More Info",
            value="Visit the RARSMS web dashboard for message history and account management.",
            inline=False
        )

        await ctx.send(embed=embed)