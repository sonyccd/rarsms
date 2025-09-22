#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from .base import BaseNotifier, NotificationData

logger = logging.getLogger(__name__)

class FileNotifier(BaseNotifier):
    """File-based notification provider for logging to disk"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.log_file = config.get('log_file', '/app/logs/aprs_notifications.log')
        self.format = config.get('format', 'json')  # 'json' or 'text'
        self.max_file_size = self._parse_size(config.get('max_file_size', '10MB'))
        self.backup_count = config.get('backup_count', 5)

    def is_configured(self) -> bool:
        """Check if file configuration is valid"""
        try:
            # Ensure directory exists
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def send_notification(self, data: NotificationData) -> bool:
        """Write notification to file"""
        try:
            # Rotate file if needed
            self._rotate_if_needed()

            # Create log entry
            if self.format == 'json':
                log_entry = self._create_json_entry(data)
            else:
                log_entry = self._create_text_entry(data)

            # Write to file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')

            logger.debug(f"Logged notification for {data.callsign} to {self.log_file}")
            return True

        except Exception as e:
            logger.error(f"Error writing to log file: {e}")
            return False

    def _create_json_entry(self, data: NotificationData) -> str:
        """Create JSON log entry"""
        entry = {
            'timestamp': data.timestamp.isoformat(),
            'callsign': data.callsign,
            'base_callsign': data.base_callsign,
            'packet_type': data.packet_type,
            'raw_packet': data.raw_packet
        }

        if data.has_position():
            entry['position'] = data.position

        if data.has_message():
            entry['message'] = data.message

        return json.dumps(entry, separators=(',', ':'))

    def _create_text_entry(self, data: NotificationData) -> str:
        """Create text log entry"""
        timestamp_str = data.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        entry = f"[{timestamp_str}] {data.callsign} ({data.packet_type})"

        if data.has_position():
            entry += f" LOC:{data.get_location_string()}"

        if data.has_message():
            msg_text = data.get_message_text().replace('\n', ' | ')
            entry += f" MSG:{msg_text}"

        entry += f" RAW:{data.raw_packet}"

        return entry

    def _rotate_if_needed(self):
        """Rotate log file if it exceeds max size"""
        try:
            if not os.path.exists(self.log_file):
                return

            if os.path.getsize(self.log_file) < self.max_file_size:
                return

            # Rotate existing backup files
            for i in range(self.backup_count - 1, 0, -1):
                old_file = f"{self.log_file}.{i}"
                new_file = f"{self.log_file}.{i + 1}"

                if os.path.exists(old_file):
                    if i == self.backup_count - 1:
                        os.remove(old_file)  # Remove oldest backup
                    else:
                        os.rename(old_file, new_file)

            # Move current file to .1
            os.rename(self.log_file, f"{self.log_file}.1")

            logger.info(f"Rotated log file: {self.log_file}")

        except Exception as e:
            logger.warning(f"Error rotating log file: {e}")

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '10MB' to bytes"""
        size_str = size_str.upper().strip()

        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)  # Assume bytes

    def validate_config(self) -> tuple[bool, str]:
        """Validate file configuration"""
        try:
            # Check if directory is writable
            log_dir = Path(self.log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            # Test write access
            test_file = log_dir / '.test_write'
            test_file.write_text('test')
            test_file.unlink()

            return True, "File configuration valid"

        except Exception as e:
            return False, f"Cannot write to log directory: {e}"