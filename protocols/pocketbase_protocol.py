#!/usr/bin/env python3

import asyncio
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from .base import BaseProtocol, Message, MessageType, ProtocolCapabilities

logger = logging.getLogger(__name__)

class PocketBaseProtocol(BaseProtocol):
    """Protocol for storing messages in PocketBase database"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.pb_url = config.get('pocketbase_url', 'http://localhost:8090')
        self.collection_name = config.get('collection_name', 'messages')

    def get_capabilities(self) -> ProtocolCapabilities:
        """PocketBase can only receive messages (storage), not send"""
        return ProtocolCapabilities(
            can_send=False,  # Storage protocol - doesn't send messages
            can_receive=True,  # Can store incoming messages
            supports_position=True,  # Can store position data
            supports_threading=True,  # Can store thread/reply data
            supports_attachments=False,
            max_message_length=None
        )

    async def connect(self) -> bool:
        """Connect to PocketBase"""
        try:
            # Test connection with health check
            response = requests.get(f"{self.pb_url}/api/health", timeout=5)
            if response.status_code == 200:
                self.is_connected = True
                logger.info(f"✓ PocketBase connected at {self.pb_url}")
                return True
            else:
                logger.error(f"✗ PocketBase health check failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"✗ Failed to connect to PocketBase at {self.pb_url}: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from PocketBase"""
        self.is_connected = False
        logger.info("PocketBase connection closed")
        return True

    async def send_message(self, message: Message) -> bool:
        """Store message in PocketBase database"""
        if not self.is_connected:
            logger.error("PocketBase not connected")
            return False

        try:
            # Prepare message data for PocketBase
            data = {
                'message_id': message.message_id,
                'source_protocol': message.source_protocol,
                'source_id': message.source_id,
                'message_type': message.message_type.value,
                'content': message.content,
                'timestamp': message.timestamp.isoformat() + 'Z',
                'thread_id': message.thread_id or '',
                'reply_to': message.reply_to or '',
            }

            # Add position data if available
            position = message.get_position()
            if position:
                data['latitude'] = position.get('lat', 0)
                data['longitude'] = position.get('lon', 0)
            else:
                data['latitude'] = 0
                data['longitude'] = 0

            # Add target protocols as JSON
            if message.target_protocols:
                data['target_protocols'] = message.target_protocols

            # Add metadata as JSON
            if message.metadata:
                data['metadata'] = message.metadata

            # Add raw packet if available
            raw_packet = message.metadata.get('raw_packet') if message.metadata else None
            data['raw_packet'] = raw_packet or ''

            # POST to PocketBase API
            response = requests.post(
                f"{self.pb_url}/api/collections/{self.collection_name}/records",
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                logger.debug(f"✓ Stored message {message.message_id} from {message.source_id} in PocketBase")
                return True
            else:
                logger.error(f"✗ Failed to store message {message.message_id}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"✗ Error storing message {message.message_id} in PocketBase: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if PocketBase protocol is properly configured"""
        return bool(self.pb_url and self.collection_name)

    def format_message_for_protocol(self, message: Message) -> str:
        """Not used for storage protocols"""
        return ""

    def parse_incoming_message(self, raw_data: Any) -> Optional[Message]:
        """Not used for storage protocols"""
        return None