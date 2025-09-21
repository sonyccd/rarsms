#!/usr/bin/env python3
"""Main entry point for RARSMS Discord Bot."""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

import structlog
import discord

from config import Config, load_config, validate_config
from database import DatabaseClient
from bot import RARSMSBot

# Version information
VERSION = "1.0.0"

# Global bot instance for signal handling
bot_instance = None


def setup_logging(config: Config):
    """Setup structured logging."""
    if config.logging.format == "json":
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    # Set Discord.py logging level to reduce noise
    discord_logger = structlog.get_logger("discord")
    discord_logger.setLevel("WARNING")


async def signal_handler(sig_num):
    """Handle shutdown signals."""
    logger = structlog.get_logger()
    logger.info("Received shutdown signal", signal=sig_num)

    if bot_instance:
        logger.info("Shutting down bot")
        await bot_instance.close()

    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if tasks:
        logger.info("Cancelling pending tasks", count=len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("Shutdown complete")


def main():
    """Main entry point."""
    global bot_instance

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="RARSMS Discord Bot")
    parser.add_argument(
        "--config",
        type=str,
        default="/app/config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"RARSMS Discord Bot v{VERSION}"
    )
    args = parser.parse_args()

    try:
        # Load and validate configuration
        config = load_config(args.config)
        validate_config(config)

        # Setup logging
        setup_logging(config)
        logger = structlog.get_logger()

        logger.info(
            "Starting RARSMS Discord Bot",
            version=VERSION,
            config_file=args.config
        )

        # Check if service is enabled
        if not config.service.enabled:
            logger.info("Discord bot service is disabled in configuration")
            sys.exit(0)

        # Run the bot
        asyncio.run(run_bot(config))

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


async def run_bot(config: Config):
    """Run the Discord bot with proper error handling."""
    global bot_instance

    logger = structlog.get_logger()

    # Setup signal handlers
    if sys.platform != "win32":
        for sig in [signal.SIGINT, signal.SIGTERM]:
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(signal_handler(s))
            )

    # Create database client
    database = DatabaseClient(config.database)

    try:
        # Connect to database
        await database.connect()

        # Initialize system status
        await database.update_system_status(
            service="discord-bot",
            status="starting",
            metadata={
                "version": VERSION,
                "started_at": discord.utils.utcnow().isoformat()
            }
        )

        # Create and start bot
        bot_instance = RARSMSBot(config, database)

        logger.info("Starting Discord bot")
        await bot_instance.start(config.discord.token)

    except discord.LoginFailure:
        logger.error("Invalid Discord token")
        await database.update_system_status(
            service="discord-bot",
            status="error",
            metadata={"error": "Invalid Discord token"}
        )
        raise
    except discord.HTTPException as e:
        logger.error("Discord HTTP error", error=str(e))
        await database.update_system_status(
            service="discord-bot",
            status="error",
            metadata={"error": f"Discord HTTP error: {e}"}
        )
        raise
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        await database.update_system_status(
            service="discord-bot",
            status="error",
            metadata={"error": f"Unexpected error: {e}"}
        )
        raise
    finally:
        # Cleanup
        if bot_instance and not bot_instance.is_closed():
            await bot_instance.close()

        # Update final status
        await database.update_system_status(
            service="discord-bot",
            status="offline",
            metadata={
                "stopped_at": discord.utils.utcnow().isoformat(),
                "shutdown_reason": "normal"
            }
        )

        await database.close()
        logger.info("Discord bot stopped")


if __name__ == "__main__":
    main()