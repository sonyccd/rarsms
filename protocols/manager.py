#!/usr/bin/env python3

import asyncio
import logging
from typing import Dict, Any, List, Type, Optional, Set
from .base import BaseProtocol, Message, MessageType
from .interchange import UniversalMessage, MessageAdapter, ContentPriority

logger = logging.getLogger(__name__)

class ProtocolManager:
    """Manages multiple communication protocols and handles message routing"""

    def __init__(self):
        self.protocols: Dict[str, BaseProtocol] = {}
        self.registry: Dict[str, Type[BaseProtocol]] = {}
        self.routing_rules: List[Dict[str, Any]] = []
        self.message_history: List[Message] = []
        self.universal_message_history: List[UniversalMessage] = []
        self.max_history = 1000

        # Message adaptation system
        self.message_adapter = MessageAdapter()

        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'messages_routed': 0,
            'messages_adapted': 0,
            'routing_errors': 0,
            'adaptation_errors': 0
        }

    def register_protocol_type(self, name: str, protocol_class: Type[BaseProtocol]):
        """Register a protocol class for later instantiation"""
        self.registry[name] = protocol_class
        logger.info(f"Registered protocol type: {name}")

    def add_protocol(self, protocol_name: str, protocol_type: str, config: Dict[str, Any]) -> bool:
        """Add a protocol instance"""
        try:
            if protocol_type not in self.registry:
                logger.error(f"Unknown protocol type: {protocol_type}")
                return False

            if protocol_name in self.protocols:
                logger.warning(f"Protocol {protocol_name} already exists, replacing...")

            protocol_class = self.registry[protocol_type]
            protocol = protocol_class(protocol_name, config)

            if not protocol.is_configured():
                logger.error(f"Protocol {protocol_name} is not properly configured")
                return False

            # Set message callback for routing
            protocol.set_message_callback(self._on_message_received)

            self.protocols[protocol_name] = protocol
            logger.info(f"Added protocol: {protocol_name} ({protocol_type})")
            return True

        except Exception as e:
            logger.error(f"Error adding protocol {protocol_name}: {e}")
            return False

    async def connect_all(self) -> Dict[str, bool]:
        """Connect all configured protocols"""
        results = {}

        for name, protocol in self.protocols.items():
            try:
                logger.info(f"Connecting protocol: {name}")
                success = await protocol.connect()
                results[name] = success

                if success:
                    logger.info(f"Protocol {name} connected successfully")
                else:
                    logger.error(f"Failed to connect protocol: {name}")

            except Exception as e:
                logger.error(f"Error connecting protocol {name}: {e}")
                results[name] = False

        connected_count = sum(1 for success in results.values() if success)
        logger.info(f"Connected {connected_count}/{len(self.protocols)} protocols")

        return results

    async def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect all protocols"""
        results = {}

        for name, protocol in self.protocols.items():
            try:
                success = await protocol.disconnect()
                results[name] = success
            except Exception as e:
                logger.error(f"Error disconnecting protocol {name}: {e}")
                results[name] = False

        return results

    def add_routing_rule(self,
                        source_protocols: List[str],
                        target_protocols: List[str],
                        message_types: Optional[List[MessageType]] = None,
                        source_filter: Optional[str] = None,
                        bidirectional: bool = False):
        """Add a message routing rule"""
        rule = {
            'source_protocols': source_protocols,
            'target_protocols': target_protocols,
            'message_types': message_types or list(MessageType),
            'source_filter': source_filter,
            'bidirectional': bidirectional
        }

        self.routing_rules.append(rule)

        if bidirectional:
            # Add reverse rule
            reverse_rule = {
                'source_protocols': target_protocols,
                'target_protocols': source_protocols,
                'message_types': message_types or list(MessageType),
                'source_filter': source_filter,
                'bidirectional': False  # Prevent infinite recursion
            }
            self.routing_rules.append(reverse_rule)

        logger.info(f"Added routing rule: {source_protocols} -> {target_protocols}")

    def _convert_message_to_universal(self, message: Message) -> UniversalMessage:
        """Convert legacy Message to UniversalMessage format"""
        try:
            universal_msg = UniversalMessage(
                message_id=message.message_id,
                source_protocol=message.source_protocol,
                source_id=message.source_id,
                timestamp=message.timestamp,
                message_type=message.message_type,
                metadata=message.metadata.copy()
            )

            # Determine content priority based on message type
            if message.message_type == MessageType.EMERGENCY:
                priority = ContentPriority.CRITICAL
            elif message.message_type == MessageType.POSITION:
                priority = ContentPriority.HIGH
            else:
                priority = ContentPriority.HIGH

            # Add main content
            if message.content:
                universal_msg.add_text(message.content, priority)

            # Add position if available
            if hasattr(message, 'get_position') and message.get_position():
                pos = message.get_position()
                universal_msg.add_location(
                    pos['lat'], pos['lon'],
                    f"Position: {pos['lat']:.4f}, {pos['lon']:.4f}",
                    ContentPriority.MEDIUM
                )

            # Don't add metadata as content for APRS replies - keep them clean
            if not message.metadata.get('reply_to_aprs', False):
                # Add metadata as low-priority content
                for key, value in message.metadata.items():
                    if key not in ['position', 'raw_packet', 'addressed_to_rarsms', 'has_rarsms_prefix']:
                        universal_msg.add_metadata(key, str(value), ContentPriority.LOW)

                # Add source identification
                universal_msg.add_content_block(
                    f"From: {message.source_protocol}:{message.source_id}",
                    ContentPriority.MEDIUM,
                    'metadata',
                    can_omit=True
                )

            # Copy routing information
            universal_msg.target_protocols = message.target_protocols.copy()
            universal_msg.target_ids = message.target_ids.copy()
            universal_msg.thread_id = message.thread_id
            universal_msg.reply_to = message.reply_to

            return universal_msg

        except Exception as e:
            logger.error(f"Error converting message to universal format: {e}")
            # Fallback to basic conversion
            return UniversalMessage(
                message_id=message.message_id,
                source_protocol=message.source_protocol,
                source_id=message.source_id,
                timestamp=message.timestamp,
                message_type=message.message_type
            ).add_text(message.content or "Message conversion error", ContentPriority.HIGH)

    async def send_universal_message(self, universal_message: UniversalMessage) -> int:
        """
        Send a universal message to target protocols with automatic adaptation

        Args:
            universal_message: UniversalMessage to send

        Returns:
            int: Number of successful sends
        """
        success_count = 0

        for target_protocol_name in universal_message.target_protocols:
            if target_protocol_name not in self.protocols:
                logger.warning(f"Target protocol '{target_protocol_name}' not available")
                continue

            try:
                target_protocol = self.protocols[target_protocol_name]

                # Don't route back to source protocol
                if target_protocol_name == universal_message.source_protocol:
                    continue

                # Get target protocol capabilities
                capabilities = target_protocol.get_capabilities()

                # Adapt message for target protocol
                adapted_messages = self.message_adapter.adapt_message(
                    universal_message, capabilities, target_protocol_name
                )

                self.stats['messages_adapted'] += len(adapted_messages)

                # Send each adapted message
                for adapted_msg_data in adapted_messages:
                    # Convert back to legacy Message format for protocol
                    legacy_message = Message(
                        source_protocol=adapted_msg_data['source_protocol'],
                        source_id=adapted_msg_data['source_id'],
                        message_type=adapted_msg_data['message_type'],
                        content=adapted_msg_data['content'],
                        timestamp=adapted_msg_data['timestamp'],
                        metadata=adapted_msg_data.get('metadata', {})
                    )

                    # Copy additional fields
                    if 'target_id' in adapted_msg_data:
                        legacy_message.target_ids[target_protocol_name] = adapted_msg_data['target_id']

                    # Send via protocol
                    success = await target_protocol.send_message(legacy_message)
                    if success:
                        success_count += 1
                        self.stats['messages_sent'] += 1
                        logger.info(f"📤 Sent adapted message to {target_protocol_name}")
                    else:
                        self.stats['routing_errors'] += 1
                        logger.warning(f"❌ Failed to send message to {target_protocol_name}")

            except Exception as e:
                logger.error(f"Error sending to {target_protocol_name}: {e}")
                self.stats['adaptation_errors'] += 1

        return success_count

    def _on_message_received(self, message: Message):
        """Handle incoming message from any protocol"""
        try:
            self.stats['messages_received'] += 1

            # Add to legacy history
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history.pop(0)

            # Check if this is an APRS reply that should bypass universal conversion
            if message.metadata.get('reply_to_aprs', False):
                logger.info(f"📨 Received {message.message_type.value} message from {message.source_protocol}:{message.source_id}")
                # Route directly without universal conversion to preserve target_ids
                asyncio.create_task(self._route_message(message))
            else:
                # Convert to universal format
                universal_message = self._convert_message_to_universal(message)

                # Add to universal history
                self.universal_message_history.append(universal_message)
                if len(self.universal_message_history) > self.max_history:
                    self.universal_message_history.pop(0)

                logger.info(f"📨 Received {universal_message.message_type.value} message from {message.source_protocol}:{message.source_id}")

                # Apply routing rules with universal format
                asyncio.create_task(self._route_universal_message(universal_message))

        except Exception as e:
            logger.error(f"Error handling received message: {e}")

    async def _route_universal_message(self, universal_message: UniversalMessage):
        """Route universal message according to configured rules with adaptation"""
        try:
            target_protocols = []

            # Apply routing rules to determine targets
            for rule in self.routing_rules:
                if self._universal_message_matches_rule(universal_message, rule):
                    target_protocols.extend(rule['target_protocols'])

            # Remove duplicates and set targets
            unique_targets = list(set(target_protocols))
            universal_message.target_protocols = unique_targets

            if unique_targets:
                # Send with automatic adaptation
                success_count = await self.send_universal_message(universal_message)

                if success_count > 0:
                    self.stats['messages_routed'] += 1
                    logger.info(f"🔄 Routed message to {success_count}/{len(unique_targets)} protocols")
                else:
                    logger.warning(f"⚠️ Failed to route message to any of {len(unique_targets)} target protocols")
            else:
                logger.debug(f"No routing targets for {universal_message.message_type.value} message from {universal_message.source_protocol}")

        except Exception as e:
            logger.error(f"Error routing universal message: {e}")
            self.stats['routing_errors'] += 1

    def _universal_message_matches_rule(self, message: UniversalMessage, rule: Dict[str, Any]) -> bool:
        """Check if a universal message matches a routing rule"""
        # Check source protocol
        if message.source_protocol not in rule['source_protocols']:
            return False

        # Check message type
        if message.message_type not in rule['message_types']:
            return False

        # Check source filter (regex on source_id)
        if rule['source_filter']:
            import re
            if not re.search(rule['source_filter'], message.source_id):
                return False

        return True

    async def _route_message(self, message: Message):
        """Route message according to configured rules"""
        try:
            routed_count = 0

            for rule in self.routing_rules:
                if self._message_matches_rule(message, rule):
                    target_protocols = rule['target_protocols']

                    for target_protocol_name in target_protocols:
                        if target_protocol_name in self.protocols:
                            target_protocol = self.protocols[target_protocol_name]

                            # Don't route back to source protocol
                            if target_protocol_name == message.source_protocol:
                                continue

                            # Prepare message for target
                            routed_message = self._prepare_message_for_target(
                                message, target_protocol_name
                            )
                            logger.info(f"🔍 Routing to {target_protocol_name}: original_content='{message.content}', routed_content='{routed_message.content}'")

                            # Send message
                            success = await target_protocol.send_message(routed_message)
                            if success:
                                routed_count += 1
                                self.stats['messages_sent'] += 1
                            else:
                                self.stats['routing_errors'] += 1

            if routed_count > 0:
                self.stats['messages_routed'] += 1
                logger.info(f"Routed message to {routed_count} protocols")
            else:
                logger.debug(f"No routing targets for message from {message.source_protocol}")

        except Exception as e:
            logger.error(f"Error routing message: {e}")
            self.stats['routing_errors'] += 1

    def _message_matches_rule(self, message: Message, rule: Dict[str, Any]) -> bool:
        """Check if a message matches a routing rule"""
        # Check source protocol
        if message.source_protocol not in rule['source_protocols']:
            return False

        # Check message type
        if message.message_type not in rule['message_types']:
            return False

        # Check source filter (regex on source_id)
        if rule['source_filter']:
            import re
            if not re.search(rule['source_filter'], message.source_id):
                return False

        return True

    def _prepare_message_for_target(self, message: Message, target_protocol: str) -> Message:
        """Prepare a message for sending to a specific target protocol"""
        # Create a copy of the message
        routed_message = Message(
            source_protocol=message.source_protocol,
            source_id=message.source_id,
            message_type=message.message_type,
            content=message.content,
            timestamp=message.timestamp,
            metadata=message.metadata.copy()
        )

        # Add target protocol
        routed_message.add_target(target_protocol)

        # Copy target_ids from original message
        routed_message.target_ids = message.target_ids.copy()

        # Set thread/reply information if supported
        routed_message.thread_id = message.thread_id
        routed_message.reply_to = message.reply_to

        return routed_message

    async def send_message(self,
                          source_protocol: str,
                          source_id: str,
                          content: str,
                          message_type: MessageType = MessageType.TEXT,
                          target_protocols: Optional[List[str]] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send a message from the manager (useful for external integrations)"""
        try:
            message = Message(
                source_protocol=source_protocol,
                source_id=source_id,
                message_type=message_type,
                content=content,
                metadata=metadata or {}
            )

            if target_protocols:
                for protocol_name in target_protocols:
                    message.add_target(protocol_name)

                # Send directly to specified protocols
                success_count = 0
                for protocol_name in target_protocols:
                    if protocol_name in self.protocols:
                        protocol = self.protocols[protocol_name]
                        if await protocol.send_message(message):
                            success_count += 1

                return success_count > 0
            else:
                # Use routing rules
                await self._route_message(message)
                return True

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def get_protocol_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all protocols"""
        status = {}
        for name, protocol in self.protocols.items():
            status[name] = protocol.get_protocol_info()
        return status

    def get_statistics(self) -> Dict[str, Any]:
        """Get messaging statistics"""
        return self.stats.copy()

    def get_routing_rules(self) -> List[Dict[str, Any]]:
        """Get current routing rules"""
        return self.routing_rules.copy()

    def get_connected_protocols(self) -> List[str]:
        """Get list of connected protocol names"""
        return [name for name, protocol in self.protocols.items() if protocol.is_connected]

    def clear_history(self):
        """Clear message history"""
        self.message_history.clear()
        logger.info("Message history cleared")

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages as dictionaries"""
        recent = self.message_history[-limit:] if limit > 0 else self.message_history
        return [msg.to_dict() for msg in recent]