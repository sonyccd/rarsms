#!/usr/bin/env python3

import socket
import requests
import json
import time
import logging
import os
import sys
import signal
import yaml
from datetime import datetime
from notifiers.manager import NotificationManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class RARSMSBridge:
    def __init__(self):
        self.running = True
        self.aprs_socket = None
        self.config = self.load_config()
        self.authorized_callsigns = self.load_callsigns()
        self.notification_manager = NotificationManager()

        # Load notifiers from configuration
        self.notification_manager.load_notifiers_from_config(self.config)

        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def load_config(self):
        """Load configuration from environment variables and config file"""
        config = {
            'aprs_server': os.getenv('APRS_SERVER', 'rotate.aprs2.net'),
            'aprs_port': int(os.getenv('APRS_PORT', '14580')),
            'aprs_callsign': os.getenv('APRS_CALLSIGN'),
            'aprs_passcode': os.getenv('APRS_PASSCODE'),
            'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
            'filter_distance': os.getenv('APRS_FILTER_DISTANCE', '100'),
            'filter_lat': os.getenv('APRS_FILTER_LAT', '35.7796'),
            'filter_lon': os.getenv('APRS_FILTER_LON', '-78.6382')
        }

        # Try to load from config.yaml if it exists
        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r') as f:
                    yaml_config = yaml.safe_load(f)
                    config.update(yaml_config)
        except Exception as e:
            logger.warning(f"Could not load config.yaml: {e}")

        # Validate required config
        required_fields = ['aprs_callsign', 'aprs_passcode', 'discord_webhook_url']
        for field in required_fields:
            if not config.get(field):
                logger.error(f"Required configuration missing: {field}")
                sys.exit(1)

        return config

    def load_callsigns(self):
        """Load authorized callsigns from callsigns.txt"""
        callsigns = set()

        # Try to load from file
        if os.path.exists('callsigns.txt'):
            try:
                with open('callsigns.txt', 'r') as f:
                    for line in f:
                        callsign = line.strip().upper()
                        if callsign and not callsign.startswith('#'):
                            callsigns.add(callsign)
                logger.info(f"Loaded {len(callsigns)} authorized callsigns")
            except Exception as e:
                logger.error(f"Error loading callsigns.txt: {e}")

        # Also load from environment variable (comma-separated)
        env_callsigns = os.getenv('AUTHORIZED_CALLSIGNS', '')
        if env_callsigns:
            for callsign in env_callsigns.split(','):
                callsign = callsign.strip().upper()
                if callsign:
                    callsigns.add(callsign)

        if not callsigns:
            logger.warning("No authorized callsigns configured")

        return callsigns

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.aprs_socket:
            try:
                self.aprs_socket.close()
            except:
                pass

    def connect_aprs(self):
        """Connect to APRS-IS server"""
        try:
            logger.info(f"Connecting to APRS-IS: {self.config['aprs_server']}:{self.config['aprs_port']}")

            self.aprs_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.aprs_socket.settimeout(30)
            self.aprs_socket.connect((self.config['aprs_server'], self.config['aprs_port']))

            # Send login command
            login_cmd = f"user {self.config['aprs_callsign']} pass {self.config['aprs_passcode']} vers RARSMS-Bridge 1.0"

            # Add filter for position and message packets in area
            filter_cmd = f" filter r/{self.config['filter_lat']}/{self.config['filter_lon']}/{self.config['filter_distance']}"

            full_login = login_cmd + filter_cmd + "\r\n"
            logger.info(f"Sending login: {login_cmd} [filter applied]")
            self.aprs_socket.send(full_login.encode('utf-8'))

            # Wait for login response - keep reading until we get logresp
            buffer = ""
            start_time = time.time()
            timeout = 10  # 10 second timeout for login

            while time.time() - start_time < timeout:
                try:
                    data = self.aprs_socket.recv(1024).decode('utf-8', errors='ignore')
                    if not data:
                        break

                    buffer += data

                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()

                        logger.info(f"APRS-IS: {line}")

                        # Look for login response
                        if line.startswith('# logresp'):
                            if 'verified' in line.lower():
                                logger.info("Successfully logged into APRS-IS")
                                return True
                            else:
                                logger.error(f"APRS-IS login failed: {line}")
                                return False

                        # Also accept old-style responses
                        if 'verified' in line.lower() and line.startswith('#'):
                            logger.info("Successfully logged into APRS-IS (legacy response)")
                            return True

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error reading login response: {e}")
                    break

            logger.error("Timeout waiting for APRS-IS login response")
            return False

        except Exception as e:
            logger.error(f"Error connecting to APRS-IS: {e}")
            return False

    def parse_packet(self, raw_packet):
        """Parse APRS packet and extract relevant information"""
        try:
            raw_packet = raw_packet.strip()
            if not raw_packet:
                return None

            # Basic APRS packet format: CALLSIGN>DESTINATION,PATH:DATA
            if ':' not in raw_packet:
                return None

            header, data = raw_packet.split(':', 1)

            # Extract source callsign
            if '>' not in header:
                return None

            source_call = header.split('>')[0].strip()

            # Remove SSID for callsign checking but keep for display
            base_callsign = source_call.split('-')[0]

            packet_info = {
                'raw': raw_packet,
                'callsign': source_call,
                'base_callsign': base_callsign,
                'data': data,
                'timestamp': datetime.utcnow(),
                'packet_type': 'unknown',
                'position': None,
                'message': None
            }

            # Determine packet type and parse accordingly
            if data.startswith('!') or data.startswith('=') or data.startswith('@'):
                # Position packet
                packet_info['packet_type'] = 'position'
                packet_info['position'] = self.parse_position(data)

            elif data.startswith(':'):
                # Message packet
                packet_info['packet_type'] = 'message'
                packet_info['message'] = self.parse_message(data)

            return packet_info

        except Exception as e:
            logger.debug(f"Error parsing packet: {e} - Raw: {raw_packet}")
            return None

    def parse_position(self, data):
        """Parse position data from APRS packet"""
        try:
            # This is a simplified parser - APRS position formats are complex
            # Looking for basic lat/lon in various formats

            # Remove timestamp if present
            pos_data = data[1:]  # Remove ! or = or @

            if len(pos_data) < 19:
                return None

            # Try to parse basic uncompressed format: DDMM.mmN/DDDMM.mmW
            # Position starts after timestamp (if any)
            pos_start = 0
            if pos_data[6] in 'zh/':  # Timestamp indicators
                pos_start = 7

            if len(pos_data) < pos_start + 19:
                return None

            lat_str = pos_data[pos_start:pos_start+8]
            lon_str = pos_data[pos_start+9:pos_start+18]

            if len(lat_str) == 8 and len(lon_str) == 9:
                # Parse latitude DDMM.mmN
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

        except Exception as e:
            logger.debug(f"Error parsing position: {e}")

        return None

    def parse_message(self, data):
        """Parse message data from APRS packet"""
        try:
            # Message format: :ADDRESSEE:message{MSGNO}
            if not data.startswith(':'):
                return None

            msg_data = data[1:]  # Remove leading :

            # Find the second colon
            if ':' not in msg_data:
                return None

            addressee, message_part = msg_data.split(':', 1)
            addressee = addressee.strip()

            # Extract message and message number
            message = message_part
            msg_no = None

            if '{' in message and message.endswith('}'):
                # Has message number
                msg_parts = message.rsplit('{', 1)
                if len(msg_parts) == 2:
                    message = msg_parts[0]
                    msg_no = msg_parts[1][:-1]  # Remove }

            return {
                'addressee': addressee,
                'message': message,
                'msg_no': msg_no
            }

        except Exception as e:
            logger.debug(f"Error parsing message: {e}")

        return None

    def is_authorized_callsign(self, callsign):
        """Check if callsign is in the authorized list"""
        return callsign in self.authorized_callsigns

    def send_notifications(self, packet_info):
        """Send notifications to all configured providers"""
        try:
            success_count = self.notification_manager.send_notification(packet_info)

            if success_count > 0:
                logger.info(f"Sent notifications for {packet_info['callsign']} via {success_count} providers")
                return True
            else:
                logger.warning(f"Failed to send notifications for {packet_info['callsign']}")
                return False

        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
            return False

    def run(self):
        """Main application loop"""
        logger.info("Starting RARSMS APRS Bridge")
        logger.info(f"Monitoring {len(self.authorized_callsigns)} authorized callsigns")
        logger.info(f"Configured {self.notification_manager.get_notifier_count()} notification providers: {', '.join(self.notification_manager.get_notifier_names())}")

        packet_count = 0
        forwarded_count = 0

        while self.running:
            try:
                # Connect to APRS-IS
                if not self.connect_aprs():
                    logger.error("Failed to connect to APRS-IS, retrying in 30 seconds...")
                    time.sleep(30)
                    continue

                # Main packet processing loop
                buffer = ""
                while self.running:
                    try:
                        data = self.aprs_socket.recv(1024).decode('utf-8', errors='ignore')
                        if not data:
                            logger.warning("APRS-IS connection closed")
                            break

                        buffer += data

                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()

                            if not line or line.startswith('#'):
                                continue

                            packet_count += 1

                            # Parse the packet
                            packet_info = self.parse_packet(line)
                            if not packet_info:
                                continue

                            # Check if callsign is authorized
                            if not self.is_authorized_callsign(packet_info['base_callsign']):
                                logger.debug(f"Filtered packet from {packet_info['callsign']} (not authorized)")
                                continue

                            logger.info(f"Processing packet from {packet_info['callsign']} ({packet_info['packet_type']})")

                            # Send notifications
                            if self.send_notifications(packet_info):
                                forwarded_count += 1

                            # Log statistics periodically
                            if packet_count % 100 == 0:
                                logger.info(f"Statistics: {packet_count} packets received, {forwarded_count} forwarded")

                    except socket.timeout:
                        # Send keepalive
                        try:
                            self.aprs_socket.send(b"#keepalive\r\n")
                        except:
                            break
                    except Exception as e:
                        logger.error(f"Error in packet processing loop: {e}")
                        break

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            # Close socket and wait before reconnecting
            if self.aprs_socket:
                try:
                    self.aprs_socket.close()
                except:
                    pass
                self.aprs_socket = None

            if self.running:
                logger.info("Reconnecting in 10 seconds...")
                time.sleep(10)

        logger.info(f"RARSMS Bridge shutting down. Final stats: {packet_count} packets, {forwarded_count} forwarded")

if __name__ == "__main__":
    bridge = RARSMSBridge()
    bridge.run()