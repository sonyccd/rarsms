#!/usr/bin/env python3

import socket
import asyncio
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseProtocol, Message, MessageType, ProtocolCapabilities

logger = logging.getLogger(__name__)

class APRSProtocol(BaseProtocol):
    """APRS-IS protocol implementation for bidirectional communication"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)

        # APRS-IS connection settings
        self.server = config.get('aprs_server', 'rotate.aprs2.net')
        self.port = config.get('aprs_port', 14580)
        self.callsign = config.get('aprs_callsign')
        if self.callsign:
            self.callsign = self.callsign.upper()  # APRS callsigns should be uppercase
        self.passcode = config.get('aprs_passcode')

        # Geographic filtering
        self.filter_lat = config.get('filter_lat', '35.7796')
        self.filter_lon = config.get('filter_lon', '-78.6382')
        self.filter_distance = config.get('filter_distance', '100')

        # Authorization settings
        self.authorized_callsigns = set(config.get('authorized_callsigns', []))

        # Message filtering settings
        self.message_prefix = config.get('message_prefix', 'RARSMS').upper()
        self.require_prefix = config.get('require_prefix', True)

        # Connection state
        self.socket: Optional[socket.socket] = None
        self.reader_task: Optional[asyncio.Task] = None
        self.buffer = ""

        # Message deduplication
        self.message_cache = {}  # Cache recent messages to prevent duplicates
        self.cache_timeout = config.get('deduplication_timeout', 300)  # Configurable timeout in seconds

    def get_capabilities(self) -> ProtocolCapabilities:
        """APRS capabilities"""
        return ProtocolCapabilities(
            can_send=True,
            can_receive=True,
            supports_position=True,
            supports_threading=False,
            supports_attachments=False,
            max_message_length=67  # APRS message data field limit
        )

    def is_configured(self) -> bool:
        """Check if APRS is properly configured"""
        return bool(self.callsign and self.passcode)

    async def connect(self) -> bool:
        """Connect to APRS-IS server"""
        try:
            logger.info(f"Connecting to APRS-IS: {self.server}:{self.port}")

            # Create socket connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.connect, (self.server, self.port)
            )

            # Send login command
            login_cmd = f"user {self.callsign} pass {self.passcode} vers RARSMS-Bridge 2.0"
            filter_cmd = f" filter r/{self.filter_lat}/{self.filter_lon}/{self.filter_distance}"
            full_login = login_cmd + filter_cmd + "\r\n"

            logger.info(f"Sending APRS login: {login_cmd} [filter applied]")
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.send, full_login.encode('utf-8')
            )

            # Wait for login response
            if await self._wait_for_login_response():
                self.is_connected = True

                # Start reader task for incoming messages
                self.reader_task = asyncio.create_task(self._read_loop())

                logger.info(f"APRS protocol '{self.name}' connected successfully")
                return True
            else:
                logger.error(f"APRS login failed for protocol '{self.name}'")
                return False

        except Exception as e:
            logger.error(f"Error connecting APRS protocol '{self.name}': {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from APRS-IS"""
        try:
            self.is_connected = False

            # Cancel reader task
            if self.reader_task:
                self.reader_task.cancel()
                try:
                    await self.reader_task
                except asyncio.CancelledError:
                    pass
                self.reader_task = None

            # Close socket
            if self.socket:
                self.socket.close()
                self.socket = None

            logger.info(f"APRS protocol '{self.name}' disconnected")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting APRS protocol '{self.name}': {e}")
            return False

    def validate_message(self, message: Message) -> tuple[bool, str]:
        """Validate if a message can be sent via APRS with proper packet formatting"""
        logger.info(f"🔍 APRS validating message: content='{message.content}', source='{message.source_protocol}:{message.source_id}'")

        if not self.capabilities.can_send:
            return False, f"{self.name} does not support sending messages"

        if message.message_type == MessageType.POSITION and not self.capabilities.supports_position:
            return False, f"{self.name} does not support position messages"

        # For APRS messages, calculate the actual packet length including formatting
        if message.message_type == MessageType.TEXT:
            # APRS message format: :ADDRESSEE :message
            # Addressee is 9 characters + 2 colons = 11 characters overhead
            max_content_len = 67 - 11  # 56 characters for actual message content
            if len(message.content) > max_content_len:
                return False, f"Message content too long for APRS (max: {max_content_len}, got: {len(message.content)} chars): '{message.content}'"

        return True, "Message is valid"

    async def send_message(self, message: Message) -> bool:
        """Send a message via APRS-IS"""
        try:
            if not self.is_connected:
                logger.error(f"APRS protocol '{self.name}' not connected")
                return False

            # Validate message
            is_valid, error = self.validate_message(message)
            if not is_valid:
                logger.error(f"Invalid message for APRS: {error}")
                return False

            # Get target ID for APRS and ensure uppercase for consistency
            target_callsign = message.target_ids.get('aprs', 'CQ').upper()
            logger.info(f"🔍 APRS sending to target: '{target_callsign}' (from target_ids: {message.target_ids})")

            # Format based on message type
            if message.message_type == MessageType.POSITION:
                aprs_packet = self._format_position_packet(message)
            else:
                aprs_packet = self._format_message_packet(message, target_callsign)

            # Send packet
            packet_data = f"{self.callsign}>APRS,TCPIP*:{aprs_packet}\r\n"
            logger.info(f"🔍 Sending APRS packet: '{packet_data.strip()}'")
            await asyncio.get_event_loop().run_in_executor(
                None, self.socket.send, packet_data.encode('utf-8')
            )

            logger.info(f"Sent APRS message from {message.source_id} to {target_callsign}")
            return True

        except Exception as e:
            logger.error(f"Error sending APRS message: {e}")
            return False

    async def _wait_for_login_response(self) -> bool:
        """Wait for APRS-IS login response"""
        try:
            timeout = 10
            start_time = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start_time < timeout:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.socket.recv, 1024
                )

                if not data:
                    break

                response = data.decode('utf-8', errors='ignore')
                self.buffer += response

                # Process complete lines
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    line = line.strip()

                    logger.info(f"APRS-IS: {line}")

                    # Look for login response
                    if line.startswith('# logresp'):
                        return 'verified' in line.lower()
                    elif 'verified' in line.lower() and line.startswith('#'):
                        return True

            return False

        except Exception as e:
            logger.error(f"Error waiting for APRS login response: {e}")
            return False

    async def _read_loop(self):
        """Main loop for reading APRS packets"""
        try:
            while self.is_connected:
                try:
                    # Read data with timeout
                    data = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self.socket.recv, 1024
                        ),
                        timeout=30.0
                    )

                    if not data:
                        logger.warning("APRS-IS connection closed by server")
                        self.is_connected = False
                        break

                    self.buffer += data.decode('utf-8', errors='ignore')

                    # Process complete lines
                    while '\n' in self.buffer:
                        line, self.buffer = self.buffer.split('\n', 1)
                        line = line.strip()

                        if line and not line.startswith('#'):
                            await self._process_packet(line)

                except asyncio.TimeoutError:
                    # Send keepalive
                    try:
                        logger.debug("Sending APRS keepalive")
                        await asyncio.get_event_loop().run_in_executor(
                            None, self.socket.send, b"#keepalive\r\n"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send APRS keepalive: {e}")
                        break

                except Exception as e:
                    logger.error(f"Error in APRS read loop: {e}")
                    self.is_connected = False
                    break

        except asyncio.CancelledError:
            logger.debug("APRS read loop cancelled")
        except Exception as e:
            logger.error(f"APRS read loop error: {e}")
        finally:
            self.is_connected = False

    async def _process_packet(self, raw_packet: str):
        """Process incoming APRS packet"""
        try:
            message = self.parse_incoming_message(raw_packet)
            if message and self._is_authorized(message.source_id) and self._should_route_message(message):
                # Check for duplicate messages
                if self._is_duplicate_message(message):
                    logger.debug(f"Skipping duplicate message from {message.source_id}: {message.content[:50]}...")
                    return

                logger.info(f"Received APRS message from {message.source_id} ({message.message_type.value})")
                self.on_message_received(message)

        except Exception as e:
            logger.debug(f"Error processing APRS packet: {e}")

    def parse_incoming_message(self, raw_packet: str) -> Optional[Message]:
        """Parse APRS packet into standardized Message"""
        try:
            if ':' not in raw_packet:
                return None

            header, data = raw_packet.split(':', 1)

            # Extract source callsign
            if '>' not in header:
                return None

            source_call = header.split('>')[0].strip()
            base_callsign = source_call.split('-')[0]

            # Determine message type and parse content
            if data.startswith('!') or data.startswith('=') or data.startswith('@'):
                # Position packet
                position = self._parse_position(data)
                if position:
                    return Message(
                        source_protocol=self.name,
                        source_id=source_call,
                        message_type=MessageType.POSITION,
                        content=f"Position update from {source_call}",
                        metadata={
                            'position': position,
                            'raw_packet': raw_packet
                        }
                    )

            elif data.startswith(':'):
                # Message packet
                message_data = self._parse_message(data)
                if message_data:
                    # Check if message is addressed to RARSMS or starts with prefix
                    content = message_data['message']
                    addressee = message_data['addressee'].strip()

                    # If addressed to RARSMS, remove prefix from content if present
                    if addressee.upper() == self.message_prefix:
                        # Message addressed to RARSMS - content is the actual message
                        actual_content = content
                    elif content.upper().startswith(self.message_prefix):
                        # Message starts with RARSMS prefix - remove it
                        actual_content = content[len(self.message_prefix):].strip()
                        # Remove leading colon or space if present
                        if actual_content.startswith(':') or actual_content.startswith(' '):
                            actual_content = actual_content[1:].strip()
                    else:
                        # No RARSMS prefix - use full content but mark for filtering
                        actual_content = content

                    return Message(
                        source_protocol=self.name,
                        source_id=source_call,
                        message_type=MessageType.TEXT,
                        content=actual_content,
                        metadata={
                            'addressee': addressee,
                            'original_message': content,
                            'msg_no': message_data.get('msg_no'),
                            'raw_packet': raw_packet,
                            'addressed_to_rarsms': addressee.upper() == self.message_prefix,
                            'has_rarsms_prefix': content.upper().startswith(self.message_prefix)
                        }
                    )

            return None

        except Exception as e:
            logger.debug(f"Error parsing APRS packet: {e}")
            return None

    def _parse_position(self, data: str) -> Optional[Dict[str, float]]:
        """Parse APRS position data"""
        try:
            # Remove leading indicator
            pos_data = data[1:]

            # Skip timestamp if present
            pos_start = 0
            if len(pos_data) > 6 and pos_data[6] in 'zh/':
                pos_start = 7

            if len(pos_data) < pos_start + 19:
                return None

            lat_str = pos_data[pos_start:pos_start+8]
            lon_str = pos_data[pos_start+9:pos_start+18]

            if len(lat_str) == 8 and len(lon_str) == 9:
                if lat_str[7] in 'NS' and lon_str[8] in 'EW':
                    lat_deg = float(lat_str[:2])
                    lat_min = float(lat_str[2:7])
                    lat = lat_deg + lat_min / 60.0
                    if lat_str[7] == 'S':
                        lat = -lat

                    lon_deg = float(lon_str[:3])
                    lon_min = float(lon_str[3:8])
                    lon = lon_deg + lon_min / 60.0
                    if lon_str[8] == 'W':
                        lon = -lon

                    return {'lat': lat, 'lon': lon}

        except Exception:
            pass

        return None

    def _parse_message(self, data: str) -> Optional[Dict[str, str]]:
        """Parse APRS message data"""
        try:
            if not data.startswith(':'):
                return None

            msg_data = data[1:]
            if ':' not in msg_data:
                return None

            addressee, message_part = msg_data.split(':', 1)
            addressee = addressee.strip()

            message = message_part
            msg_no = None

            if '{' in message and message.endswith('}'):
                msg_parts = message.rsplit('{', 1)
                if len(msg_parts) == 2:
                    message = msg_parts[0]
                    msg_no = msg_parts[1][:-1]

            return {
                'addressee': addressee,
                'message': message,
                'msg_no': msg_no
            }

        except Exception:
            pass

        return None

    def _format_message_packet(self, message: Message, target_callsign: str) -> str:
        """Format message as APRS message packet"""
        # APRS message format: :ADDRESSEE :message{MSGNO}
        # Addressee must be exactly 9 characters, padded with spaces
        # Convert to uppercase for consistency
        addressee = target_callsign.upper().ljust(9)  # Convert to uppercase and pad to 9 characters
        msg_content = message.content

        # Generate message number for acknowledgment tracking
        # Use last 3 digits of current timestamp for simplicity
        import time
        msg_number = str(int(time.time()))[-3:]

        # Account for message number in length calculation
        msg_number_part = f"{{{msg_number}"
        max_content_len = 67 - 11 - len(msg_number_part)  # Total limit minus addressee, formatting, and msg number

        # Truncate if too long
        if len(msg_content) > max_content_len:
            msg_content = msg_content[:max_content_len-3] + "..."

        # Log the formatted components to verify format
        logger.debug(f"🔍 APRS addressee field: '{addressee}' (length: {len(addressee)})")
        logger.debug(f"🔍 APRS message number: '{msg_number}'")

        return f":{addressee}:{msg_content}{msg_number_part}"

    def _format_position_packet(self, message: Message) -> str:
        """Format message as APRS position packet"""
        position = message.get_position()
        if not position:
            return f">{message.content}"

        lat = position['lat']
        lon = position['lon']

        # Convert to APRS format DDMM.mmN/DDDMM.mmW
        lat_deg = int(abs(lat))
        lat_min = (abs(lat) - lat_deg) * 60
        lat_dir = 'N' if lat >= 0 else 'S'

        lon_deg = int(abs(lon))
        lon_min = (abs(lon) - lon_deg) * 60
        lon_dir = 'E' if lon >= 0 else 'W'

        lat_str = f"{lat_deg:02d}{lat_min:05.2f}{lat_dir}"
        lon_str = f"{lon_deg:03d}{lon_min:05.2f}{lon_dir}"

        return f"!{lat_str}/{lon_str}> {message.content}"

    def _is_authorized(self, callsign: str) -> bool:
        """Check if callsign is authorized"""
        if not self.authorized_callsigns:
            return True  # If no filter, allow all

        base_callsign = callsign.split('-')[0].upper()
        return base_callsign in self.authorized_callsigns

    def _should_route_message(self, message: Message) -> bool:
        """Check if message should be routed based on RARSMS prefix rules"""
        # Always route position messages from authorized callsigns
        if message.message_type == MessageType.POSITION:
            return True

        # For text messages, check RARSMS prefix requirement
        if message.message_type == MessageType.TEXT and self.require_prefix:
            metadata = message.metadata

            # Allow if message was addressed to RARSMS
            if metadata.get('addressed_to_rarsms', False):
                logger.info(f"Routing message addressed to {self.message_prefix} from {message.source_id}")
                return True

            # Allow if message starts with RARSMS prefix
            if metadata.get('has_rarsms_prefix', False):
                logger.info(f"Routing message with {self.message_prefix} prefix from {message.source_id}")
                return True

            # Block other messages
            logger.debug(f"Blocking message from {message.source_id} - no {self.message_prefix} prefix")
            return False

        # Default behavior - route if prefix not required
        return not self.require_prefix

    def _is_duplicate_message(self, message: Message) -> bool:
        """Check if this message is a duplicate of a recently processed message"""
        import time
        import hashlib
        current_time = time.time()

        # For APRS messages, use raw packet for more accurate deduplication
        # if available, otherwise fall back to content-based deduplication
        raw_packet = message.metadata.get('raw_packet', '')

        if raw_packet:
            # Use source callsign + message content from raw packet
            # This avoids issues with different packet routing paths
            if ':' in raw_packet and ('>' in raw_packet):
                try:
                    header_part = raw_packet.split(':', 1)[0]
                    data_part = raw_packet.split(':', 1)[1]
                    source_call = header_part.split('>')[0]

                    # For message packets, extract the actual message content
                    if data_part.startswith(':') and ':' in data_part[1:]:
                        # Message format: :ADDRESSEE :MESSAGE
                        msg_parts = data_part[1:].split(':', 1)
                        if len(msg_parts) == 2:
                            content_for_dedup = msg_parts[1]
                            # Remove message number if present
                            if '{' in content_for_dedup:
                                content_for_dedup = content_for_dedup.split('{')[0]
                        else:
                            content_for_dedup = data_part
                    else:
                        content_for_dedup = data_part

                    message_key = f"{source_call}:{message.message_type.value}:{content_for_dedup}"
                except:
                    # Fallback to simple content-based key
                    message_key = f"{message.source_id}:{message.message_type.value}:{message.content}"
            else:
                message_key = f"{message.source_id}:{message.message_type.value}:{message.content}"
        else:
            # Fallback for messages without raw packet
            message_key = f"{message.source_id}:{message.message_type.value}:{message.content}"

        # Clean up expired entries from cache
        expired_keys = [k for k, timestamp in self.message_cache.items()
                       if current_time - timestamp > self.cache_timeout]
        for key in expired_keys:
            del self.message_cache[key]

        # Check if this message was recently processed
        if message_key in self.message_cache:
            logger.info(f"🚫 Blocked duplicate message from {message.source_id}: {message.content[:30]}...")
            return True

        # Add this message to the cache
        self.message_cache[message_key] = current_time
        logger.debug(f"✅ New message cached: {message_key[:50]}...")
        return False