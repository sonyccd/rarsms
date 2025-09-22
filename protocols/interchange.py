#!/usr/bin/env python3

import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from .base import MessageType, ProtocolCapabilities

logger = logging.getLogger(__name__)

class ContentPriority(Enum):
    """Priority levels for content adaptation"""
    CRITICAL = 1    # Must be preserved (emergency info)
    HIGH = 2        # Important (main message)
    MEDIUM = 3      # Useful (metadata, timestamps)
    LOW = 4         # Optional (formatting, extra info)

@dataclass
class ContentBlock:
    """Individual content block with adaptation metadata"""
    content: str
    priority: ContentPriority
    content_type: str  # 'text', 'location', 'timestamp', 'metadata', 'media'
    min_length: int = 0  # Minimum length if truncated
    can_truncate: bool = True
    can_omit: bool = False
    fallback_text: Optional[str] = None

@dataclass
class UniversalMessage:
    """Universal message format that adapts to any protocol"""

    # Core identification
    message_id: str
    source_protocol: str
    source_id: str
    timestamp: datetime

    # Message classification
    message_type: MessageType
    urgency: ContentPriority = ContentPriority.MEDIUM

    # Content blocks (ordered by importance)
    content_blocks: List[ContentBlock] = field(default_factory=list)

    # Structured data
    position: Optional[Dict[str, float]] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Routing information
    target_protocols: List[str] = field(default_factory=list)
    target_ids: Dict[str, str] = field(default_factory=dict)

    # Threading/conversation
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None

    def __post_init__(self):
        """Initialize message ID if not provided"""
        if not self.message_id:
            import uuid
            self.message_id = str(uuid.uuid4())[:8]

    def add_content_block(self, content: str, priority: ContentPriority,
                         content_type: str = 'text', **kwargs) -> 'UniversalMessage':
        """Add a content block to the message"""
        block = ContentBlock(
            content=content,
            priority=priority,
            content_type=content_type,
            **kwargs
        )
        self.content_blocks.append(block)
        return self

    def add_text(self, text: str, priority: ContentPriority = ContentPriority.HIGH) -> 'UniversalMessage':
        """Add primary text content"""
        return self.add_content_block(text, priority, 'text')

    def add_location(self, lat: float, lon: float,
                    description: str = "", priority: ContentPriority = ContentPriority.MEDIUM) -> 'UniversalMessage':
        """Add location information"""
        self.position = {'lat': lat, 'lon': lon}
        if description:
            self.add_content_block(description, priority, 'location')
        return self

    def add_metadata(self, key: str, value: str,
                    priority: ContentPriority = ContentPriority.LOW) -> 'UniversalMessage':
        """Add metadata as content block"""
        self.metadata[key] = value
        self.add_content_block(f"{key}: {value}", priority, 'metadata', can_omit=True)
        return self

    def get_primary_content(self) -> str:
        """Get the main text content (highest priority text blocks)"""
        text_blocks = [b for b in self.content_blocks
                      if b.content_type == 'text' and b.priority in [ContentPriority.CRITICAL, ContentPriority.HIGH]]
        return ' '.join(b.content for b in text_blocks)

    def get_full_content(self) -> str:
        """Get all content concatenated"""
        return ' '.join(b.content for b in self.content_blocks)

class MessageAdapter:
    """Adapts universal messages to specific protocol capabilities"""

    def __init__(self):
        self.adaptation_strategies = {
            'truncate_low_priority': self._truncate_low_priority,
            'abbreviate_metadata': self._abbreviate_metadata,
            'compact_location': self._compact_location,
            'remove_formatting': self._remove_formatting,
            'split_message': self._split_message
        }

    def adapt_message(self, message: UniversalMessage,
                     target_capabilities: ProtocolCapabilities,
                     target_protocol: str) -> List[Dict[str, Any]]:
        """
        Adapt a universal message to target protocol capabilities

        Returns list of protocol-specific message dictionaries
        """
        try:
            # Start with all content blocks sorted by priority
            blocks = sorted(message.content_blocks, key=lambda x: x.priority.value)

            # Apply protocol-specific adaptations
            adapted_blocks = self._apply_protocol_adaptations(blocks, target_capabilities, target_protocol)

            # Fit content to protocol limits
            fitted_blocks = self._fit_to_protocol_limits(adapted_blocks, target_capabilities)

            # Generate final message(s)
            return self._generate_protocol_messages(message, fitted_blocks, target_capabilities, target_protocol)

        except Exception as e:
            logger.error(f"Error adapting message for {target_protocol}: {e}")
            # Fallback to basic content
            return [{'content': message.get_primary_content()[:target_capabilities.max_message_length or 100]}]

    def _apply_protocol_adaptations(self, blocks: List[ContentBlock],
                                   capabilities: ProtocolCapabilities,
                                   target_protocol: str) -> List[ContentBlock]:
        """Apply protocol-specific content adaptations"""
        adapted_blocks = []

        for block in blocks:
            adapted_block = ContentBlock(
                content=block.content,
                priority=block.priority,
                content_type=block.content_type,
                min_length=block.min_length,
                can_truncate=block.can_truncate,
                can_omit=block.can_omit,
                fallback_text=block.fallback_text
            )

            # Protocol-specific adaptations
            if target_protocol.startswith('aprs'):
                adapted_block = self._adapt_for_aprs(adapted_block)
            elif target_protocol.startswith('discord'):
                adapted_block = self._adapt_for_discord(adapted_block)
            elif target_protocol.startswith('slack'):
                adapted_block = self._adapt_for_slack(adapted_block)

            # Apply general adaptations
            if not capabilities.supports_attachments and block.content_type == 'media':
                # Convert media to text description
                adapted_block.content = f"[Media: {block.content}]"
                adapted_block.content_type = 'text'

            adapted_blocks.append(adapted_block)

        return adapted_blocks

    def _adapt_for_aprs(self, block: ContentBlock) -> ContentBlock:
        """APRS-specific adaptations"""
        if block.content_type == 'location' and 'maps.google.com' in block.content:
            # Remove map links for APRS
            block.content = re.sub(r'https?://[^\s]+', '', block.content).strip()

        # Remove Discord/Slack formatting
        block.content = re.sub(r'[*_~`]', '', block.content)  # Remove markdown
        block.content = re.sub(r'<[^>]+>', '', block.content)  # Remove HTML/mentions

        # APRS prefers concise messages
        if block.content_type == 'metadata':
            block.can_omit = True

        return block

    def _adapt_for_discord(self, block: ContentBlock) -> ContentBlock:
        """Discord-specific adaptations"""
        if block.content_type == 'location':
            # Add Discord-friendly formatting
            if 'lat' in str(block.content) and 'lon' in str(block.content):
                # Convert coordinates to map link
                coords = re.search(r'(-?\d+\.?\d*),?\s*(-?\d+\.?\d*)', block.content)
                if coords:
                    lat, lon = coords.groups()
                    map_url = f"https://maps.google.com/?q={lat},{lon}"
                    block.content = f"📍 Location: [{lat}, {lon}]({map_url})"

        # Discord supports rich formatting
        if block.content_type == 'metadata':
            block.content = f"**{block.content}**"  # Bold metadata

        return block

    def _adapt_for_slack(self, block: ContentBlock) -> ContentBlock:
        """Slack-specific adaptations"""
        # Convert Discord markdown to Slack format
        block.content = re.sub(r'\*\*(.*?)\*\*', r'*\1*', block.content)  # Bold
        block.content = re.sub(r'\*(.*?)\*', r'_\1_', block.content)      # Italic

        return block

    def _fit_to_protocol_limits(self, blocks: List[ContentBlock],
                               capabilities: ProtocolCapabilities) -> List[ContentBlock]:
        """Fit content to protocol message length limits"""
        if not capabilities.max_message_length:
            return blocks

        max_length = capabilities.max_message_length
        fitted_blocks = []
        current_length = 0

        # Add blocks in priority order until we hit the limit
        for block in blocks:
            block_length = len(block.content)

            if current_length + block_length <= max_length:
                # Block fits completely
                fitted_blocks.append(block)
                current_length += block_length
            elif block.can_truncate:
                # Try to truncate block
                available_space = max_length - current_length
                if available_space >= block.min_length:
                    truncated_content = self._smart_truncate(block.content, available_space)
                    truncated_block = ContentBlock(
                        content=truncated_content,
                        priority=block.priority,
                        content_type=block.content_type
                    )
                    fitted_blocks.append(truncated_block)
                    break  # No more space
                elif block.fallback_text and len(block.fallback_text) <= available_space:
                    # Use fallback text
                    fallback_block = ContentBlock(
                        content=block.fallback_text,
                        priority=block.priority,
                        content_type=block.content_type
                    )
                    fitted_blocks.append(fallback_block)
                    break
            elif not block.can_omit:
                # Must include critical content
                if block.priority == ContentPriority.CRITICAL:
                    # Force truncate critical content
                    available_space = max_length - current_length
                    if available_space > 10:  # Minimum viable message
                        truncated_content = self._smart_truncate(block.content, available_space)
                        fitted_blocks.append(ContentBlock(
                            content=truncated_content,
                            priority=block.priority,
                            content_type=block.content_type
                        ))
                break  # No more space

        return fitted_blocks

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Intelligently truncate text at word boundaries"""
        if len(text) <= max_length:
            return text

        # Try to truncate at sentence boundary
        sentences = text.split('. ')
        truncated = ""
        for sentence in sentences:
            test_text = truncated + sentence + ". "
            if len(test_text) <= max_length - 3:  # Save space for "..."
                truncated = test_text
            else:
                break

        if truncated:
            return truncated.rstrip() + "..."

        # Fallback to word boundary
        words = text.split(' ')
        truncated = ""
        for word in words:
            test_text = truncated + word + " "
            if len(test_text) <= max_length - 3:
                truncated = test_text
            else:
                break

        return truncated.rstrip() + "..." if truncated else text[:max_length-3] + "..."

    def _generate_protocol_messages(self, message: UniversalMessage,
                                   blocks: List[ContentBlock],
                                   capabilities: ProtocolCapabilities,
                                   target_protocol: str) -> List[Dict[str, Any]]:
        """Generate final protocol-specific message format"""

        # Combine all content blocks
        content = ' '.join(block.content for block in blocks if block.content.strip())

        # Base message structure
        protocol_message = {
            'content': content,
            'message_id': message.message_id,
            'source_protocol': message.source_protocol,
            'source_id': message.source_id,
            'timestamp': message.timestamp,
            'message_type': message.message_type,
            'metadata': message.metadata.copy()
        }

        # Add protocol-specific features
        if capabilities.supports_position and message.position:
            protocol_message['position'] = message.position

        if capabilities.supports_threading and message.thread_id:
            protocol_message['thread_id'] = message.thread_id

        if capabilities.supports_attachments and message.attachments:
            protocol_message['attachments'] = message.attachments

        # Add target routing info
        if message.target_ids.get(target_protocol):
            protocol_message['target_id'] = message.target_ids[target_protocol]

        return [protocol_message]

    def _truncate_low_priority(self, blocks: List[ContentBlock], target_length: int) -> List[ContentBlock]:
        """Remove low priority blocks to fit length"""
        # Implementation for truncation strategy
        pass

    def _abbreviate_metadata(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Abbreviate metadata blocks"""
        # Implementation for metadata abbreviation
        pass

    def _compact_location(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Compact location information"""
        # Implementation for location compacting
        pass

    def _remove_formatting(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Remove rich text formatting"""
        # Implementation for formatting removal
        pass

    def _split_message(self, message: UniversalMessage, capabilities: ProtocolCapabilities) -> List[Dict[str, Any]]:
        """Split message into multiple parts if needed"""
        # Implementation for message splitting
        pass

# Convenience functions for creating universal messages

def create_text_message(source_protocol: str, source_id: str, text: str,
                       priority: ContentPriority = ContentPriority.HIGH) -> UniversalMessage:
    """Create a simple text message"""
    return UniversalMessage(
        message_id="",
        source_protocol=source_protocol,
        source_id=source_id,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT
    ).add_text(text, priority)

def create_position_message(source_protocol: str, source_id: str,
                          lat: float, lon: float, comment: str = "") -> UniversalMessage:
    """Create a position/location message"""
    msg = UniversalMessage(
        message_id="",
        source_protocol=source_protocol,
        source_id=source_id,
        timestamp=datetime.utcnow(),
        message_type=MessageType.POSITION
    ).add_location(lat, lon, comment)

    if comment:
        msg.add_text(comment, ContentPriority.MEDIUM)

    return msg

def create_emergency_message(source_protocol: str, source_id: str,
                           emergency_text: str, lat: float = None, lon: float = None) -> UniversalMessage:
    """Create an emergency message"""
    msg = UniversalMessage(
        message_id="",
        source_protocol=source_protocol,
        source_id=source_id,
        timestamp=datetime.utcnow(),
        message_type=MessageType.EMERGENCY,
        urgency=ContentPriority.CRITICAL
    ).add_content_block(f"🚨 EMERGENCY: {emergency_text}", ContentPriority.CRITICAL, 'text')

    if lat is not None and lon is not None:
        msg.add_location(lat, lon, "Emergency location", ContentPriority.CRITICAL)

    return msg