#!/usr/bin/env python3

import asyncio
import logging
import os
import sys
import signal
import yaml
from typing import Dict, Any, List
from datetime import datetime

# Import protocol system
from protocols.manager import ProtocolManager
from protocols.aprs import APRSProtocol
from protocols.discord import DiscordProtocol
from protocols.base import MessageType

# Import notification system (backward compatibility)
from notifiers.manager import NotificationManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class RARSMSBridge:
    """RARSMS Bridge with protocol abstraction for bidirectional communication"""

    def __init__(self):
        self.running = True
        self.config = self.load_config()

        # Initialize protocol manager
        self.protocol_manager = ProtocolManager()
        self._register_protocol_types()

        # Initialize notification manager (for backward compatibility)
        self.notification_manager = NotificationManager()
        self.notification_manager.load_notifiers_from_config(self.config)

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables and config file"""
        config = {
            # APRS-IS Configuration
            'aprs_server': os.getenv('APRS_SERVER', 'rotate.aprs2.net'),
            'aprs_port': int(os.getenv('APRS_PORT', '14580')),
            'aprs_callsign': os.getenv('APRS_CALLSIGN'),
            'aprs_passcode': os.getenv('APRS_PASSCODE'),
            'filter_distance': os.getenv('APRS_FILTER_DISTANCE', '100'),
            'filter_lat': os.getenv('APRS_FILTER_LAT', '35.7796'),
            'filter_lon': os.getenv('APRS_FILTER_LON', '-78.6382'),

            # Discord Configuration (backward compatibility)
            'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
            'discord_bot_token': os.getenv('DISCORD_BOT_TOKEN'),
            'discord_channel_id': os.getenv('DISCORD_CHANNEL_ID'),
            'discord_username': os.getenv('DISCORD_USERNAME', 'RARSMS Bridge'),

            # APRS Message Filtering
            'message_prefix': os.getenv('MESSAGE_PREFIX', 'RARSMS'),
            'require_prefix': os.getenv('REQUIRE_PREFIX', 'true').lower() == 'true',
        }

        # Try to load from config.yaml if it exists
        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        config.update(yaml_config)
        except Exception as e:
            logger.warning(f"Could not load config.yaml: {e}")

        # Load authorized callsigns
        config['authorized_callsigns'] = self.load_callsigns()

        return config

    def load_callsigns(self) -> List[str]:
        """Load authorized callsigns from callsigns.txt"""
        callsigns = []

        # Try to load from file
        if os.path.exists('callsigns.txt'):
            try:
                with open('callsigns.txt', 'r') as f:
                    for line in f:
                        callsign = line.strip().upper()
                        if callsign and not callsign.startswith('#'):
                            callsigns.append(callsign)
                logger.info(f"Loaded {len(callsigns)} authorized callsigns")
            except Exception as e:
                logger.error(f"Error loading callsigns.txt: {e}")

        # Also load from environment variable (comma-separated)
        env_callsigns = os.getenv('AUTHORIZED_CALLSIGNS', '')
        if env_callsigns:
            for callsign in env_callsigns.split(','):
                callsign = callsign.strip().upper()
                if callsign:
                    callsigns.append(callsign)

        return callsigns

    def _register_protocol_types(self):
        """Register available protocol types"""
        self.protocol_manager.register_protocol_type('aprs', APRSProtocol)
        self.protocol_manager.register_protocol_type('discord', DiscordProtocol)

    def setup_protocols(self):
        """Setup protocol instances from configuration"""
        try:
            logger.info("Setting up communication protocols...")

            # Setup APRS protocol
            if self.config.get('aprs_callsign') and self.config.get('aprs_passcode'):
                aprs_config = {
                    'aprs_server': self.config['aprs_server'],
                    'aprs_port': self.config['aprs_port'],
                    'aprs_callsign': self.config['aprs_callsign'],
                    'aprs_passcode': self.config['aprs_passcode'],
                    'filter_lat': self.config['filter_lat'],
                    'filter_lon': self.config['filter_lon'],
                    'filter_distance': self.config['filter_distance'],
                    'authorized_callsigns': self.config['authorized_callsigns'],
                    'message_prefix': self.config.get('message_prefix', 'RARSMS'),
                    'require_prefix': self.config.get('require_prefix', True)
                }

                success = self.protocol_manager.add_protocol('aprs_main', 'aprs', aprs_config)
                if success:
                    logger.info("✓ APRS protocol configured successfully")
                else:
                    logger.error("✗ Failed to configure APRS protocol")
            else:
                missing = []
                if not self.config.get('aprs_callsign'):
                    missing.append('APRS_CALLSIGN')
                if not self.config.get('aprs_passcode'):
                    missing.append('APRS_PASSCODE')
                logger.warning(f"⚠ APRS protocol not configured - missing: {', '.join(missing)}")
                logger.info("  → APRS will not be available for message routing")

            # Setup Discord protocol
            webhook_url = self.config.get('discord_webhook_url')
            if webhook_url and webhook_url.strip() and webhook_url.startswith('https://discord.com/api/webhooks/'):
                discord_config = {
                    'discord_webhook_url': webhook_url,
                    'discord_bot_token': self.config.get('discord_bot_token'),
                    'discord_channel_id': self.config.get('discord_channel_id'),
                    'discord_username': self.config['discord_username'],
                }

                success = self.protocol_manager.add_protocol('discord_main', 'discord', discord_config)
                if success:
                    bidirectional = " (bidirectional)" if self.config.get('discord_bot_token') else " (send-only)"
                    logger.info(f"✓ Discord protocol configured successfully{bidirectional}")
                else:
                    logger.error("✗ Failed to configure Discord protocol")
            else:
                if not webhook_url:
                    logger.warning("⚠ Discord protocol not configured - missing: DISCORD_WEBHOOK_URL")
                elif not webhook_url.strip():
                    logger.warning("⚠ Discord protocol not configured - DISCORD_WEBHOOK_URL is empty")
                else:
                    logger.warning("⚠ Discord protocol not configured - invalid webhook URL format")
                logger.info("  → Discord will not be available for message routing")
                logger.info("  → Set DISCORD_WEBHOOK_URL to enable Discord integration")

            # Setup additional protocols from configuration
            protocols_config = self.config.get('protocols', {}) or {}
            for protocol_name, protocol_config in protocols_config.items():
                if protocol_config.get('enabled', True):
                    protocol_type = protocol_config.get('type')
                    if protocol_type:
                        success = self.protocol_manager.add_protocol(
                            protocol_name, protocol_type, protocol_config
                        )
                        if success:
                            logger.info(f"Additional protocol '{protocol_name}' configured")
                        else:
                            logger.error(f"Failed to configure protocol '{protocol_name}'")

        except Exception as e:
            logger.error(f"Error setting up protocols: {e}")

    def setup_routing_rules(self):
        """Setup message routing rules"""
        try:
            # Default rule: Route all messages between APRS and Discord
            self.protocol_manager.add_routing_rule(
                source_protocols=['aprs_main'],
                target_protocols=['discord_main'],
                message_types=[MessageType.TEXT, MessageType.POSITION],
                bidirectional=True
            )

            # Load custom routing rules from configuration
            routing_config = self.config.get('routing', {}) or {}
            for rule_name, rule_config in routing_config.items():
                if rule_config.get('enabled', True):
                    self.protocol_manager.add_routing_rule(
                        source_protocols=rule_config.get('source_protocols', []),
                        target_protocols=rule_config.get('target_protocols', []),
                        message_types=[MessageType[mt.upper()] for mt in rule_config.get('message_types', ['TEXT'])],
                        source_filter=rule_config.get('source_filter'),
                        bidirectional=rule_config.get('bidirectional', False)
                    )
                    logger.info(f"Added routing rule: {rule_name}")

        except Exception as e:
            logger.error(f"Error setting up routing rules: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    async def run(self):
        """Main application loop"""
        try:
            logger.info("Starting RARSMS Communication Bridge")

            # Setup protocols and routing
            self.setup_protocols()
            self.setup_routing_rules()

            # Display configuration summary
            protocol_status = self.protocol_manager.get_protocol_status()

            if len(protocol_status) == 0:
                logger.error("═" * 60)
                logger.error("❌ NO PROTOCOLS CONFIGURED")
                logger.error("═" * 60)
                logger.error("The bridge needs at least one protocol to function.")
                logger.error("")
                logger.error("To configure APRS (amateur radio):")
                logger.error("  • Set APRS_CALLSIGN environment variable")
                logger.error("  • Set APRS_PASSCODE environment variable")
                logger.error("  • Add authorized callsigns to callsigns.txt")
                logger.error("")
                logger.error("To configure Discord:")
                logger.error("  • Set DISCORD_WEBHOOK_URL environment variable")
                logger.error("  • Get webhook URL from Discord channel settings")
                logger.error("")
                logger.error("Example .env file:")
                logger.error("  APRS_CALLSIGN=YOUR-CALL")
                logger.error("  APRS_PASSCODE=12345")
                logger.error("  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
                logger.error("═" * 60)
                return

            logger.info("═" * 50)
            logger.info(f"📋 CONFIGURED PROTOCOLS: {len(protocol_status)}")
            logger.info("═" * 50)
            for name, info in protocol_status.items():
                caps = info['capabilities']
                status_icon = "📡" if name.startswith('aprs') else "💬" if name.startswith('discord') else "🔗"
                direction = "↔️" if caps['can_send'] and caps['can_receive'] else "📤" if caps['can_send'] else "📥"
                logger.info(f"  {status_icon} {name}: {direction} send={caps['can_send']}, receive={caps['can_receive']}")
                if caps['supports_position']:
                    logger.info(f"    └── 📍 Position support enabled")

            # Show backward compatibility status
            notifier_count = self.notification_manager.get_notifier_count()
            if notifier_count > 0:
                logger.info(f"📌 Legacy notifications: {notifier_count} providers configured")

            # Connect all protocols
            logger.info("🔌 Connecting to all protocols...")
            connection_results = await self.protocol_manager.connect_all()

            connected_protocols = [name for name, success in connection_results.items() if success]
            if not connected_protocols:
                logger.error("❌ No protocols connected successfully.")
                logger.error("Check your credentials and network connectivity.")
                logger.error("View logs above for specific connection errors.")
                return

            logger.info("═" * 50)
            logger.info(f"✅ SUCCESSFULLY CONNECTED: {len(connected_protocols)} protocol(s)")
            logger.info("═" * 50)
            for protocol_name in connected_protocols:
                logger.info(f"  🟢 {protocol_name}")

            # Provide routing context based on connected protocols
            if len(connected_protocols) == 1:
                protocol_name = connected_protocols[0]
                logger.warning("⚠️  SINGLE PROTOCOL MODE")
                if protocol_name.startswith('aprs'):
                    logger.info("  → APRS is connected but no other protocols available")
                    logger.info("  → Messages from APRS will be logged but not routed elsewhere")
                    logger.info("  → Configure Discord to enable APRS↔Discord bridging")
                elif protocol_name.startswith('discord'):
                    logger.info("  → Discord is connected but no other protocols available")
                    logger.info("  → Messages from Discord will be logged but not routed elsewhere")
                    logger.info("  → Configure APRS to enable APRS↔Discord bridging")

                # Show legacy notification fallback
                if self.notification_manager.get_notifier_count() > 0:
                    logger.info("  → Legacy notification system will still send alerts")
            else:
                logger.info("🚀 BRIDGING MODE ACTIVE")
                logger.info("  → Messages will be routed between all connected protocols")

                # Show specific routing paths
                aprs_connected = any(p.startswith('aprs') for p in connected_protocols)
                discord_connected = any(p.startswith('discord') for p in connected_protocols)

                if aprs_connected and discord_connected:
                    logger.info("  → APRS ↔ Discord bridging enabled")
                    logger.info("  → RARSMS prefix filtering active for APRS messages")

            logger.info("═" * 50)

            # Periodic status reporting
            last_stats_time = asyncio.get_event_loop().time()
            stats_interval = 300  # 5 minutes

            while self.running:
                try:
                    await asyncio.sleep(10)  # Check every 10 seconds

                    # Report statistics periodically
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_stats_time >= stats_interval:
                        stats = self.protocol_manager.get_statistics()
                        logger.info(f"Statistics: {stats['messages_received']} received, "
                                  f"{stats['messages_sent']} sent, {stats['messages_routed']} routed")
                        last_stats_time = current_time

                        # Check protocol health
                        connected = self.protocol_manager.get_connected_protocols()
                        if len(connected) < len(connected_protocols):
                            logger.warning(f"Some protocols disconnected. Connected: {', '.join(connected)}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")

        except Exception as e:
            logger.error(f"Error in main application: {e}")
        finally:
            # Cleanup
            logger.info("Shutting down protocols...")
            await self.protocol_manager.disconnect_all()

            # Final statistics
            final_stats = self.protocol_manager.get_statistics()
            logger.info(f"Final statistics: {final_stats}")
            logger.info("RARSMS Bridge shutdown complete")

def main():
    """Main entry point"""
    try:
        bridge = RARSMSBridge()
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()