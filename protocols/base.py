#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    """Types of messages that can be sent between protocols"""
    TEXT = "text"
    POSITION = "position"
    STATUS = "status"
    EMERGENCY = "emergency"

class Message:
    """Standardized message format for cross-protocol communication"""

    def __init__(self,
                 source_protocol: str,
                 source_id: str,
                 message_type: MessageType,
                 content: str,
                 timestamp: Optional[datetime] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.source_protocol = source_protocol
        self.source_id = source_id  # callsign, user ID, etc.
        self.message_type = message_type
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

        # Routing information
        self.target_protocols: List[str] = []
        self.target_ids: Dict[str, str] = {}  # protocol -> target_id mapping

        # Message tracking
        self.message_id = self._generate_id()
        self.thread_id: Optional[str] = None
        self.reply_to: Optional[str] = None

    def _generate_id(self) -> str:
        """Generate unique message ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def add_target(self, protocol: str, target_id: Optional[str] = None):
        """Add a target protocol for message routing"""
        if protocol not in self.target_protocols:
            self.target_protocols.append(protocol)
        if target_id:
            self.target_ids[protocol] = target_id

    def get_position(self) -> Optional[Dict[str, float]]:
        """Extract position data if this is a position message"""
        if self.message_type == MessageType.POSITION:
            return self.metadata.get('position')
        return None

    def is_emergency(self) -> bool:
        """Check if this is an emergency message"""
        return self.message_type == MessageType.EMERGENCY

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            'message_id': self.message_id,
            'source_protocol': self.source_protocol,
            'source_id': self.source_id,
            'message_type': self.message_type.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'target_protocols': self.target_protocols,
            'target_ids': self.target_ids,
            'thread_id': self.thread_id,
            'reply_to': self.reply_to
        }

class ProtocolCapabilities:
    """Defines what capabilities a protocol supports"""

    def __init__(self,
                 can_send: bool = True,
                 can_receive: bool = True,
                 supports_position: bool = False,
                 supports_threading: bool = False,
                 supports_attachments: bool = False,
                 max_message_length: Optional[int] = None):
        self.can_send = can_send
        self.can_receive = can_receive
        self.supports_position = supports_position
        self.supports_threading = supports_threading
        self.supports_attachments = supports_attachments
        self.max_message_length = max_message_length

class BaseProtocol(ABC):
    """Abstract base class for communication protocols"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_connected = False
        self.capabilities = self.get_capabilities()
        self.message_callback: Optional[Callable[[Message], None]] = None

    @abstractmethod
    def get_capabilities(self) -> ProtocolCapabilities:
        """Return the capabilities of this protocol"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the protocol service"""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the protocol service"""
        pass

    @abstractmethod
    async def send_message(self, message: Message) -> bool:
        """Send a message via this protocol"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this protocol is properly configured"""
        pass

    def set_message_callback(self, callback: Callable[[Message], None]):
        """Set callback for receiving messages from this protocol"""
        self.message_callback = callback

    def on_message_received(self, message: Message):
        """Called when a message is received from this protocol"""
        if self.message_callback:
            self.message_callback(message)

    def validate_message(self, message: Message) -> tuple[bool, str]:
        """Validate if a message can be sent via this protocol"""
        if not self.capabilities.can_send:
            return False, f"{self.name} does not support sending messages"

        if message.message_type == MessageType.POSITION and not self.capabilities.supports_position:
            return False, f"{self.name} does not support position messages"

        if (self.capabilities.max_message_length and
            len(message.content) > self.capabilities.max_message_length):
            return False, f"Message too long for {self.name} (max: {self.capabilities.max_message_length})"

        return True, "Message is valid"

    def format_message_for_protocol(self, message: Message) -> str:
        """Format a message for sending via this specific protocol"""
        # Default implementation - override in subclasses for protocol-specific formatting
        formatted = f"[{message.source_protocol}] {message.source_id}: {message.content}"

        if message.message_type == MessageType.POSITION and message.get_position():
            pos = message.get_position()
            formatted += f" (Location: {pos['lat']:.4f}, {pos['lon']:.4f})"

        return formatted

    def parse_incoming_message(self, raw_data: Any) -> Optional[Message]:
        """Parse incoming protocol-specific data into a standardized Message"""
        # Override in subclasses for protocol-specific parsing
        return None

    def get_protocol_info(self) -> Dict[str, Any]:
        """Get information about this protocol instance"""
        return {
            'name': self.name,
            'connected': self.is_connected,
            'capabilities': {
                'can_send': self.capabilities.can_send,
                'can_receive': self.capabilities.can_receive,
                'supports_position': self.capabilities.supports_position,
                'supports_threading': self.capabilities.supports_threading,
                'supports_attachments': self.capabilities.supports_attachments,
                'max_message_length': self.capabilities.max_message_length
            }
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"